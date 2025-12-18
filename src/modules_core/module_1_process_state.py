# src/modules_core/module_1_process_state.py
# 功能：负责进程的创建、初始化生成以及状态转换的核心逻辑

import random
from typing import List, Optional
from src.process_model import Process, ProcessState
from src.system_status import STATUS

# 辅助函数：安全地从队列中移除进程
def _safe_remove_from_deque(d: 'deque[Process]', process: Process):
    """从 deque 中安全移除一个对象，避免 ValueError。"""
    try:
        # 为了安全移除，先转为列表操作再转回 deque
        # 注意：这在大数据量下效率较低，但对于演示用的少量进程是可以接受的
        temp_list = list(d)
        if process in temp_list:
            temp_list.remove(process)
            d.clear()
            d.extend(temp_list)
    except Exception as e:
        print(f"Error removing process {process.pid}: {e}")

def generate_initial_processes(count=10) -> List[Process]:
    """
    生成初始进程列表（默认10个）。
    其中约 20% 的进程会被初始化为 BLOCKED 状态，其余为 READY。
    """
    new_processes = []

    with STATUS._lock:
        # 获取当前最大的 PID，确保 ID 不重复
        max_pid = 0
        if STATUS.all_processes:
            max_pid = max(STATUS.all_processes.keys())

        start_pid = max_pid + 1

        for i in range(start_pid, start_pid + count):
            # 随机生成属性
            arrival_time = round(random.uniform(0.0, 2.0), 2) # 初始进程到达时间较早
            burst_time = round(random.uniform(3.0, 15.0), 2)
            priority = random.randint(1, 10)

            proc = Process(
                pid=i,
                arrival_time=arrival_time,
                burst_time=burst_time,
                priority=priority
            )
            
            # 注册到全局字典
            STATUS.all_processes[proc.pid] = proc
            new_processes.append(proc)
            
            # 保持NEW状态，不立即转换
            # 进程将通过调度器的NEW状态处理机制转换到READY
            # 这样用户可以在界面上看到"新建"状态
            pass

    return new_processes


def transition_state(process: Process, new_state: ProcessState, cpu_id: Optional[int] = None,
                     already_locked: bool = False):
    """
    执行进程状态转换，并更新全局状态及其队列。
    核心逻辑：从旧队列移除 -> 更新状态 -> 加入新队列 -> 记录时间。
    """
    # 锁机制：支持外部已加锁或内部自动加锁
    if not already_locked:
        STATUS._lock.acquire()

    try:
        old_state = process.state
        
        # 如果状态没变，直接返回（除了 RUNNING -> RUNNING 这种可能更新时间的）
        if old_state == new_state and new_state != ProcessState.RUNNING:
            return

        process.state = new_state
        # print(f"PID {process.pid}: {old_state.name} -> {new_state.name}") # 调试用

        # 1. === 离开旧状态/队列 ===
        if old_state == ProcessState.READY:
            _safe_remove_from_deque(STATUS.ready_queue, process)

        elif old_state == ProcessState.BLOCKED:
            _safe_remove_from_deque(STATUS.blocked_queue, process)

        elif old_state == ProcessState.RUNNING:
            # 从运行字典中移除
            keys_to_remove = []
            for cid, p in STATUS.running_processes.items():
                if p and p.pid == process.pid:
                    keys_to_remove.append(cid)
            for k in keys_to_remove:
                STATUS.running_processes[k] = None

        # 2. === 进入新状态/队列 ===
        if new_state == ProcessState.READY:
            STATUS.ready_queue.append(process)

        elif new_state == ProcessState.BLOCKED:
            STATUS.blocked_queue.append(process)

        elif new_state == ProcessState.RUNNING:
            if cpu_id is not None:
                STATUS.running_processes[cpu_id] = process
            # 如果是第一次运行，记录开始时间
            if process.start_time == -1:
                process.start_time = STATUS.global_timer

        elif new_state == ProcessState.TERMINATED:
            process.finish_time = STATUS.global_timer
            # 计算周转时间 = 完成时间 - 到达时间
            process.turnaround_time = process.finish_time - process.arrival_time

    finally:
        if not already_locked:
            STATUS._lock.release()