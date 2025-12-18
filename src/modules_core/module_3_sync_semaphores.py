# src/modules_core/module_3_sync_semaphores.py
#基于信号量的同步逻辑

import time
import random
from threading import Semaphore
from src.system_status import SystemStatus
from src.utils_concurrency import start_simulation_thread

STATUS = SystemStatus()
# 真实线程信号量用于控制执行，全局状态信号量用于可视化
_real_semaphore = Semaphore(1)


def P_operation(thread_name):
    """
    P (Wait) 操作：尝试获取资源。
    """
    print(f"[{thread_name}] trying P_operation...")

    # 真实信号量阻塞线程执行
    if not _real_semaphore.acquire(blocking=False):
        # 如果获取失败（信号量为0），则线程进入模拟阻塞状态
        with STATUS._lock:
            if thread_name not in STATUS.blocked_queue:
                STATUS.blocked_queue.append(thread_name)
                # 记录可视化事件：线程进入阻塞队列 [cite: 29]
                print(f"[{thread_name}] BLOCKED. Blocked Queue: {STATUS.blocked_queue}")

        # 实际阻塞线程，直到信号量可用
        _real_semaphore.acquire()

        # 被唤醒后，从阻塞队列中移除
        with STATUS._lock:
            if thread_name in STATUS.blocked_queue:
                STATUS.blocked_queue.remove(thread_name)
                # 记录可视化事件：线程被唤醒
                print(f"[{thread_name}] WAKEN UP.")

    # P操作成功，更新全局状态中的信号量取值 (用于可视化) [cite: 29]
    with STATUS._lock:
        STATUS.semaphore_value = 0  # 临界区保护，信号量通常减1，这里用二值信号量模拟资源占用
        print(f"[{thread_name}] ENTERED Critical Section. Semaphore Value: {STATUS.semaphore_value}")


def V_operation(thread_name):
    """
    V (Signal) 操作：释放资源。
    """
    with STATUS._lock:
        STATUS.semaphore_value = 1  # 释放资源，信号量加1
        print(f"[{thread_name}] EXITED Critical Section. Semaphore Value: {STATUS.semaphore_value}")

    # 真实信号量释放
    _real_semaphore.release()
    # 释放时会唤醒一个等待线程 (由 Python 线程库处理)


def critical_section_task(name):
    """
    模拟一个线程竞争临界资源并执行任务。
    """
    while True:
        time.sleep(random.uniform(0.5, 1.5))  # 模拟线程在临界区外工作

        P_operation(name)

        # ==== 临界区 ====
        print(f"[{name}] is running in the CRITICAL SECTION.")
        time.sleep(random.uniform(0.1, 0.5))
        # ==== 临界区结束 ====

        V_operation(name)

        time.sleep(random.uniform(0.5, 1.5))


def start_sync_simulation(num_threads=5):
    """
    启动信号量同步演示：创建竞争临界区的线程。
    """
    threads = []
    for i in range(num_threads):
        thread = start_simulation_thread(critical_section_task, args=(f"Thread-{i}",))
        threads.append(thread)
    return threads