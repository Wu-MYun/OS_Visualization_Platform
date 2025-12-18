# src/modules_core/module_4_multicore_scheduler.py
# 功能：CPU 调度器线程 + IO 管理器线程

from threading import Thread
import time
import random
from typing import List, Optional

from config import NUM_CPUS, TIME_SLICE
from src.system_status import STATUS
from src.process_model import Process, ProcessState
from src.modules_core.module_1_process_state import transition_state

SCHEDULER_INTERVAL = 0.05  # 模拟步进时间间隔 (秒)

class IOManager(Thread):
    """
    IO 管理器线程：
    模拟外部设备中断。它会周期性地检查阻塞队列，
    并随机“唤醒”阻塞的进程（模拟 I/O 完成），将其移回就绪队列。
    """
    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        print("IO Manager started.")
        while self._running:
            time.sleep(SCHEDULER_INTERVAL * 5)  # IO 检查频率比 CPU 慢一些

            with STATUS._lock:
                if STATUS.blocked_queue:
                    # 50% 的概率唤醒队首进程，模拟不确定的 IO 时间
                    if random.random() > 0.5:
                        proc = STATUS.blocked_queue[0] # 获取但不移除，通过 transition_state 移除
                        # print(f"[IO Manager] Process {proc.pid} IO completed. Waking up...")
                        transition_state(proc, ProcessState.READY, already_locked=True)
            
            if not STATUS.scheduler_running:
                # 如果主调度器停止了，IO 也暂停工作
                pass

class CPUScheduler(Thread):
    """
    CPU 核心调度线程：
    模拟单个 CPU 核心的工作：取指(Dispatch) -> 执行(Execute)。
    """
    def __init__(self, cpu_id: int, algorithm: str = 'FCFS'):
        super().__init__()
        self.cpu_id = cpu_id
        self.algorithm = algorithm
        self._running = True
        self.current_process: Optional[Process] = None
        self.time_slice_counter = 0.0

    def stop(self):
        self._running = False

    def run(self):
        print(f"CPU Core {self.cpu_id} started ({self.algorithm}).")

        while self._running:
            # 只有Core 0处理NEW状态的进程转换，避免多个核心重复处理
            if self.cpu_id == 0:
                self._check_new_processes()
                
            # 如果当前没有进程，尝试调度
            if self.current_process is None:
                self._dispatch_process()

            # 如果有进程，执行
            if self.current_process:
                self._execute_process()
            else:
                # 空闲状态
                time.sleep(SCHEDULER_INTERVAL)

            # Core 0 负责推进全局系统时钟
            if self.cpu_id == 0 and self._running:
                self._advance_global_timer()

        # 停止后的清理
        if self.current_process:
            with STATUS._lock:
                self.current_process.cpu_id = None
                STATUS.running_processes[self.cpu_id] = None

    def _check_new_processes(self):
        """检查NEW状态的进程并将它们转换到READY状态"""
        with STATUS._lock:
            # 遍历所有进程，找到NEW状态的进程
            for process in STATUS.all_processes.values():
                if process.state == ProcessState.NEW:
                    # 50%概率将NEW状态的进程转换到READY，增加随机性
                    if random.random() < 0.5:
                        # 记录状态转换
                        print(f"[Core {self.cpu_id}] Process {process.pid} NEW -> READY")
                        transition_state(process, ProcessState.READY, already_locked=True)

    def _dispatch_process(self):
        """调度逻辑：从就绪队列选一个进程"""
        with STATUS._lock:
            if not STATUS.ready_queue:
                return

            # --- 算法逻辑分支 ---
            process_to_run = None
            
            if self.algorithm == 'Priority':
                # 优先级调度：遍历队列找优先级最高的 (数值越小优先级越高 或 反之，这里假设数值大优先级高)
                # 使用 max 获取优先级最高的进程
                process_to_run = max(STATUS.ready_queue, key=lambda p: p.priority)
                # 因为 deque 不能像 list 一样 pop(index)，我们需要先移除它
                # transition_state 会处理移除，所以这里只需选中
                
                # 特殊处理：为了让 transition_state 正常工作，我们手动调整队列顺序把选中的放到头部
                # 或者更简单：直接用 transition_state 处理，它会查找并移除
                pass 
                
            elif self.algorithm == 'SJF': # Shortest Job First
                 process_to_run = min(STATUS.ready_queue, key=lambda p: p.remaining_time)

            else: # FCFS 和 RR 都是取队首
                process_to_run = STATUS.ready_queue[0]

            if process_to_run:
                # 真正从队列移除并开始运行
                # 注意：transition_state 会负责从 ready_queue 移除它
                self.current_process = process_to_run
                self.current_process.cpu_id = self.cpu_id
                self.time_slice_counter = 0.0
                
                transition_state(self.current_process, ProcessState.RUNNING, cpu_id=self.cpu_id, already_locked=True)
                
                # 记录甘特图
                self._record_history(self.current_process.pid, STATUS.global_timer, "RUNNING")

    def _execute_process(self):
        """执行逻辑"""
        step = SCHEDULER_INTERVAL
        time.sleep(step) # 模拟耗时

        with STATUS._lock:
            if not self.current_process:
                return

            # 更新时间
            self.current_process.remaining_time -= step
            self.time_slice_counter += step

            # 检查是否完成
            if self.current_process.remaining_time <= 0:
                self.current_process.remaining_time = 0
                self._record_history(self.current_process.pid, STATUS.global_timer + step, "TERMINATED")
                transition_state(self.current_process, ProcessState.TERMINATED, already_locked=True)
                self.current_process = None
                return

            # 检查 RR 时间片轮转
            if self.algorithm == 'RR' and self.time_slice_counter >= TIME_SLICE:
                # 抢占：放回就绪队列
                self._record_history(self.current_process.pid, STATUS.global_timer + step, "PREEMPTED")
                # print(f"PID {self.current_process.pid} Time Slice used.")
                transition_state(self.current_process, ProcessState.READY, already_locked=True)
                self.current_process = None
                return

            # 模拟随机 IO 阻塞 (可选，增加动态性)
            # 只有当算法允许抢占或者自愿放弃时。这里简单模拟 1% 概率发生 IO 请求
            if random.random() < 0.01:
                self._record_history(self.current_process.pid, STATUS.global_timer + step, "BLOCKED")
                transition_state(self.current_process, ProcessState.BLOCKED, already_locked=True)
                self.current_process = None
                return

    def _advance_global_timer(self):
        """推进全局时间"""
        with STATUS._lock:
            STATUS.global_timer += SCHEDULER_INTERVAL
            # 更新所有就绪进程的等待时间
            for p in STATUS.ready_queue:
                p.wait_time += SCHEDULER_INTERVAL

    def _record_history(self, pid, time_val, event):
        if self.cpu_id not in STATUS.cpu_history:
            STATUS.cpu_history[self.cpu_id] = []
        STATUS.cpu_history[self.cpu_id].append({
            "time": time_val,
            "pid": pid,
            "event": event
        })

class SchedulerManager:
    def __init__(self, num_cpus: int = NUM_CPUS, algorithm: str = 'FCFS'):
        self.num_cpus = num_cpus
        self.algorithm = algorithm
        self.scheduler_threads: List[CPUScheduler] = []
        self.io_manager = IOManager()
        
    def update_algorithm(self, algorithm: str):
        """更新调度算法并应用到所有正在运行的调度器"""
        self.algorithm = algorithm
        # 更新所有正在运行的调度器的算法
        for scheduler in self.scheduler_threads:
            if scheduler.is_alive():
                scheduler.algorithm = algorithm
        print(f"Algorithm updated to {algorithm}.")

    def start_schedulers(self, algorithm: str = 'FCFS'):
        if STATUS.scheduler_running:
            return

        self.algorithm = algorithm
        STATUS.scheduler_running = True
        STATUS.cpu_history.clear()

        # 启动 IO 管理器
        self.io_manager = IOManager()
        self.io_manager.start()

        with STATUS._lock:
            STATUS.running_processes = {i: None for i in range(self.num_cpus)}
            self.scheduler_threads.clear()
            for i in range(self.num_cpus):
                scheduler = CPUScheduler(cpu_id=i, algorithm=self.algorithm)
                self.scheduler_threads.append(scheduler)
                scheduler.start()
            print(f"System started with {self.num_cpus} CPUs using {self.algorithm}.")

    def stop_schedulers(self):
        STATUS.scheduler_running = False
        
        # 停止 IO 管理器
        if self.io_manager and self.io_manager.is_alive():
            self.io_manager.stop()
            self.io_manager.join(timeout=1.0)

        # 停止 CPU 线程
        for scheduler in self.scheduler_threads:
            if scheduler.is_alive():
                scheduler.stop()
        
        # 等待线程结束
        for scheduler in self.scheduler_threads:
            scheduler.join(timeout=0.5)
            
        STATUS.reset_history()
        self.scheduler_threads.clear()
        print("System stopped.")

SCHEDULER_MANAGER = SchedulerManager(num_cpus=NUM_CPUS, algorithm='FCFS')