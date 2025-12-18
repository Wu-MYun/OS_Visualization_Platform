# src/utils_concurrency.py
#并发工具

from threading import Thread
from multiprocessing import Process

def start_simulation_thread(target_func, args=()):
    """
    使用 Thread 启动一个模拟任务，用于不涉及大量 CPU 运算的模块（如 IPC, 信号量）。
    """
    thread = Thread(target=target_func, args=args, daemon=True)
    thread.start()
    return thread

def start_simulation_process(target_func, args=()):
    """
    使用 Process 启动一个模拟任务，用于需要独立资源的模块（如调度器核心）。
    """
    process = Process(target=target_func, args=args, daemon=True)
    process.start()
    return process

# ... 可以在此文件中添加其他如安全队列、共享内存的辅助函数 ...