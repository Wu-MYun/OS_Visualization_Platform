# src/process_model.py
#数据模型定义

from enum import Enum


# 定义进程状态，用于模块 1 的可视化
class ProcessState(Enum):
    NEW = "新建"
    READY = "就绪"
    RUNNING = "运行"
    BLOCKED = "阻塞"
    TERMINATED = "终止"


class Process:
    """
    进程/线程基础模型，用于调度和状态管理模块。
    """

    def __init__(self, pid, arrival_time, burst_time, priority=0):
        self.pid = pid  # 进程 ID (唯一标识)
        self.state = ProcessState.NEW  # 当前状态
        self.arrival_time = arrival_time  # 到达时间
        self.burst_time = burst_time  # 总执行时间
        self.remaining_time = burst_time  # 剩余执行时间
        self.priority = priority  # 优先级 (用于 SJF/优先级调度)

        # 性能指标记录 (用于甘特图和性能输出)
        self.start_time = -1
        self.finish_time = -1
        self.wait_time = 0
        self.turnaround_time = 0
        self.response_time = None  # 响应时间：从到达就绪到首次运行的时间

    def __repr__(self):
        return f"Process(PID={self.pid}, State={self.state.name}, Burst={self.burst_time})"


class RTOS_Task(Process):
    """
    RTOS 任务模型，用于实时操作系统扩展。
    """

    def __init__(self, pid, arrival_time, burst_time, priority, period, deadline):
        super().__init__(pid, arrival_time, burst_time, priority)
        self.period = period  # 周期时间
        self.deadline = deadline  # 截止时间
        self.is_critical = False  # 是否为关键任务

    def __repr__(self):
        return f"RTOS_Task(PID={self.pid}, Priority={self.priority}, Deadline={self.deadline})"