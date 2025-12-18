# src/system_status.py (完整代码)
# 全局状态管理

from threading import RLock
from collections import deque
from typing import Dict, Any, List, Optional
# 修正 1: 导入核心模型
from src.process_model import Process, ProcessState


class SystemStatus:
    """
    全局系统状态单例类，用于在不同模块间安全地共享和更新数据。
    """
    _instance = None
    _lock = RLock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SystemStatus, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 核心调度状态
        # 修正 2: 明确指定类型为 Process
        self.all_processes: Dict[int, Process] = {}  # 所有进程的字典 {pid: Process}
        self.ready_queue: deque[Process] = deque()  # 就绪队列 (使用 deque)
        self.cpu_history: Dict[int, List[Dict]] = {}  # 多核调度历史
        self.global_timer: float = 0.0  # 模拟系统时钟
        self.cpu_threads: List[Any] = []  # 存储调度器线程引用
        self.scheduler_running: bool = False
        # 修正 3: 新增用于调度器的状态
        self.running_processes: Dict[int, Optional[Process]] = {}  # {cpu_id: Process/None}

        # IPC/同步状态 - 消息队列
        self.message_queue: deque = deque(maxlen=20)  # 消息队列内容
        
        # IPC/同步状态 - 共享内存 (新增)
        self.shm_size: int = 16 
        self.shm_data: List[str] = ["00"] * self.shm_size  # 内存数据初始值
        self.shm_ops: List[Dict[str, Any]] = []  # 记录最近的操作列表 [{'type': 'WRITE'/'READ', 'addr': 5, 'val': 'AB', 'time': time.time()}]

        self.semaphore_value: int = 1  # 信号量当前值
        self.blocked_queue: deque[tuple[str, str]] = deque()  # 信号量阻塞队列 (线程名称, 阻塞原因)
        
        # 管道IPC状态
        self.pipe_buffer: List[str] = []  # 管道缓冲区
        self.pipe_max_size: int = 5  # 管道最大容量
        self.pipe_producer_blocked: bool = False  # 管道生产者是否阻塞
        self.pipe_consumer_blocked: bool = False  # 管道消费者是否阻塞
        
        # 共享内存IPC状态 (保留原有定义并整合)
        self.shared_memory: Dict[str, Any] = {}  # 共享内存内容
        self.shared_memory_writers: Dict[int, bool] = {}  # 记录进程是否在写入共享内存
        self.shared_memory_readers: Dict[int, bool] = {}  # 记录进程是否在读取共享内存
        self.shared_memory_access_count: int = 0  # 共享内存访问计数器

        # 内存状态
        self.memory_layout: List[Dict] = []  # 内存分区状态列表
        self.page_table: Dict[int, Dict[int, int]] = {}  # 页表状态 {pid: {page: frame}}
        self.next_free_frame: int = 0

        # RTOS 状态
        self.rtos_timeline: List[Dict] = []  # 任务上下文切换记录
        self.rtos_running: bool = False
        
        # 信号量模拟状态
        self.simulation_running: bool = False

        self._initialized = True

    def reset_history(self):
        """清除历史数据，用于重置模拟"""
        with self._lock:
            self.global_timer = 0.0
            self.all_processes.clear()
            self.ready_queue.clear()
            self.message_queue.clear()
            self.blocked_queue.clear()
            self.cpu_history.clear()
            self.rtos_timeline.clear()
            self.cpu_threads.clear()
            self.running_processes.clear()
            self.scheduler_running = False
            self.rtos_running = False
            self.simulation_running = False
            
            # 重置共享内存数据
            self.shm_data = ["00"] * self.shm_size
            self.shm_last_op = {}
            
            # 重置管道IPC状态
            self.pipe_buffer.clear()
            self.pipe_producer_blocked = False
            self.pipe_consumer_blocked = False
            
            # 重置共享内存IPC状态
            self.shared_memory.clear()
            self.shared_memory_writers.clear()
            self.shared_memory_readers.clear()
            self.shared_memory_access_count = 0


# 创建并导出全局状态实例
STATUS = SystemStatus()