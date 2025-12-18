# src/modules_extension/extension_rtos.py
# 修复版 V6：引入事件唯一ID机制，彻底解决同一时刻日志丢失问题

import time
import random
from threading import Thread, Lock
from src.process_model import RTOS_Task, ProcessState
from src.system_status import SystemStatus

STATUS = SystemStatus()
rtos_lock = Lock()
rtos_thread_handle = None  

# === 全局事件计数器 (核心修复) ===
global_event_counter = 0

def get_next_event_id():
    """获取下一个全局唯一的事件ID"""
    global global_event_counter
    global_event_counter += 1
    return global_event_counter

# 模拟寄存器
cpu_registers = {f"R{i}": "0x00000000" for i in range(13)}
cpu_registers.update({
    "SP": "0x20001000", "LR": "0xFFFFFFFF", "PC": "0x08000000"
})

pending_isr = None

def generate_rtos_tasks(count=5):
    tasks = []
    STATUS.all_processes.clear() 
    for i in range(1, count + 1):
        task = RTOS_Task(
            pid=i, arrival_time=0, burst_time=random.randint(50, 200),
            priority=random.randint(2, 8), period=0, deadline=0
        )
        task.stack_base = 0x20000000 + (i * 0x400)
        task.state = ProcessState.READY  
        tasks.append(task)
        STATUS.all_processes[task.pid] = task 
    return tasks

def trigger_external_interrupt(isr_id=99):
    global pending_isr
    if not STATUS.rtos_running:
        print(f"⚠️  RTOS未启动，无法触发中断！")
        return False
    
    with rtos_lock:
        if pending_isr is None:
            burst = 300 
            isr_task = RTOS_Task(
                pid=isr_id, arrival_time=STATUS.global_timer, burst_time=burst, 
                priority=0, period=0, deadline=0
            )
            isr_task.remaining_time = burst 
            isr_task.is_isr = True
            isr_task.name = "GPIO_IRQ_Handler"
            isr_task.state = ProcessState.READY
            
            STATUS.all_processes[isr_id] = isr_task
            pending_isr = isr_task
            
            # === 核心修改：添加 ID ===
            evt_id = get_next_event_id()
            with STATUS._lock:
                STATUS.rtos_timeline.append({
                    'id': evt_id, # 新增 ID
                    'time': STATUS.global_timer,
                    'type': 'ISR_TRIGGER',
                    'prev_pid': -1,
                    'next_pid': isr_id,
                    'info': '外部硬件中断触发'
                })
            
            print(f"!!! 硬件中断触发: {isr_task.name} (Event ID: {evt_id}) !!!")
            return True
        else:
            print(f"⚠️  已有中断正在处理中")
            return False

def reset_rtos_data():
    STATUS.rtos_running = False
    STATUS.global_timer = 0
    STATUS.rtos_timeline.clear()
    STATUS.all_processes.clear()
    global pending_isr, global_event_counter
    pending_isr = None
    global_event_counter = 0 # 重置计数器
    cpu_registers.update({f"R{i}": "0x00000000" for i in range(13)})
    cpu_registers["PC"] = "0x08000000"
    cpu_registers["SP"] = "0x20001000"

class RTOS_Scheduler:
    def __init__(self, tasks: list):
        self.tasks = tasks
        self.current_task = None
        self.simulation_timer = STATUS.global_timer
        
        for t in self.tasks:
            if t.state == ProcessState.RUNNING:
                self.current_task = t
                break

    def _update_registers(self, task):
        global cpu_registers
        base = getattr(task, 'stack_base', 0x20000000)
        cpu_registers["SP"] = f"0x{base:08X}"
        cpu_registers["PC"] = f"0x0800{task.pid:04X}"
        cpu_registers["R0"] = f"0x{random.randint(0, 0xFFFFFFFF):08X}"

    def _record_event(self, event_type, prev_pid, next_pid, extra_info=""):
        # === 核心修改：自动分配 ID ===
        evt_id = get_next_event_id()
        
        event = {
            'id': evt_id, # 新增 ID
            'time': self.simulation_timer,
            'type': event_type, 
            'prev_pid': prev_pid,
            'next_pid': next_pid,
            'info': extra_info
        }
        with STATUS._lock:
            STATUS.rtos_timeline.append(event)
            if len(STATUS.rtos_timeline) > 2000:
                STATUS.rtos_timeline.pop(0)

    def run_cycle(self, time_unit=20): 
        global pending_isr
        
        while STATUS.rtos_running:
            time.sleep(0.35) 
            if not STATUS.rtos_running: break

            with rtos_lock:
                self.simulation_timer += time_unit
                STATUS.global_timer = self.simulation_timer
                
                target_task = None
                reason = ""
                
                # 1. 调度
                if pending_isr:
                    target_task = pending_isr
                    pending_isr = None 
                    reason = "Hardware IRQ"
                else:
                    for t in STATUS.all_processes.values():
                        if t.state == ProcessState.BLOCKED and random.random() < 0.1: 
                            t.state = ProcessState.READY
                            self._record_event("WAKEUP", -1, t.pid, "Sem Given")

                    ready_q = [t for t in STATUS.all_processes.values() 
                               if t.state == ProcessState.READY and t.remaining_time > 0]
                    if ready_q:
                        ready_q.sort(key=lambda x: x.priority)
                        target_task = ready_q[0]
                        reason = "Preemption"

                # 2. 切换
                if target_task != self.current_task:
                    prev_pid = self.current_task.pid if self.current_task else -1
                    next_pid = target_task.pid if target_task else -1
                    
                    if self.current_task:
                        if getattr(self.current_task, 'is_isr', False):
                             self.current_task.state = ProcessState.TERMINATED
                        elif self.current_task.state == ProcessState.RUNNING:
                            self.current_task.state = ProcessState.READY
                        
                        if next_pid != -1:
                            self._record_event("SWITCH_START", prev_pid, -1, "Save Context")

                    self.current_task = target_task
                    
                    if self.current_task:
                        self.current_task.state = ProcessState.RUNNING
                        self._update_registers(self.current_task)
                        evt_type = "ISR_EXEC" if getattr(self.current_task, 'is_isr', False) else "TASK_SWITCH"
                        self._record_event(evt_type, prev_pid, next_pid, reason)
                    else:
                        self._record_event("IDLE", prev_pid, -1, "Idle")

                # 3. 执行
                if self.current_task:
                    self.current_task.remaining_time -= time_unit
                    
                    if not getattr(self.current_task, 'is_isr', False) and random.random() < 0.05:
                        self.current_task.state = ProcessState.BLOCKED
                        self.current_task.block_reason = "Wait Queue"
                        self._record_event("BLOCKED", self.current_task.pid, -1, "Blocked")
                        self.current_task = None
                        continue

                    if self.current_task.remaining_time <= 0:
                        if getattr(self.current_task, 'is_isr', False):
                            self._record_event("ISR_FINISH", self.current_task.pid, -1, "ISR Return")
                            if self.current_task.pid in STATUS.all_processes:
                                del STATUS.all_processes[self.current_task.pid]
                        else:
                            self.current_task.state = ProcessState.TERMINATED
                            self._record_event("TASK_FINISH", self.current_task.pid, -1, "任务完成")
                        self.current_task = None

def start_rtos_simulation():
    global rtos_thread_handle
    if STATUS.rtos_running: return

    STATUS.rtos_running = True 
    
    tasks = []
    if not STATUS.all_processes:
        tasks = generate_rtos_tasks(5)
    else:
        tasks = list(STATUS.all_processes.values())
        
    scheduler = RTOS_Scheduler(tasks)
    rtos_thread_handle = Thread(target=scheduler.run_cycle, daemon=True)
    rtos_thread_handle.start()

def stop_rtos_simulation():
    STATUS.rtos_running = False