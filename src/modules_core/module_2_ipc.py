# src/modules_core/module_2_ipc.py
# 进程间通信

import time
import random
import string
from src.system_status import SystemStatus
from src.utils_concurrency import start_simulation_thread

STATUS = SystemStatus()
MAX_QUEUE_SIZE = 5  # 模拟消息队列最大容量

# 控制IPC模拟是否运行的全局标志
IPC_RUNNING = False  # 消息队列控制
IPC_SHM_RUNNING = False # 共享内存控制 (新增)


# === 1. 消息队列逻辑 ===

def producer_task(name="Producer"):
    """
    生产者任务：周期性地生成消息并放入全局消息队列。
    """
    message_id = 0
    while IPC_RUNNING:
        time.sleep(random.uniform(0.5, 2.0))  # 随机间隔生产

        # 线程安全地检查队列大小
        with STATUS._lock:
            if len(STATUS.message_queue) < MAX_QUEUE_SIZE:
                message_id += 1
                message = f"Msg-{message_id} from {name}"

                # 更新全局状态中的消息队列
                STATUS.message_queue.append(message)

                print(f"{name} produced: {message}. Queue size: {len(STATUS.message_queue)}")

            else:
                print(f"{name} waiting: Queue is full.")


def consumer_task(name="Consumer"):
    """
    消费者任务：周期性地从全局消息队列中取出消息。
    """
    while IPC_RUNNING:
        time.sleep(random.uniform(1.0, 3.0))  # 随机间隔消费

        # 线程安全地检查并取出消息
        with STATUS._lock:
            if STATUS.message_queue:
                message = STATUS.message_queue.popleft()  # 使用popleft()更高效

                print(f"{name} consumed: {message}. Queue size: {len(STATUS.message_queue)}")

            else:
                print(f"{name} waiting: Queue is empty.")

# === 2. 共享内存逻辑 (新增) ===

def shm_writer_task(name="Writer"):
    """
    写进程：随机向共享内存的某个地址写入随机数据
    """
    while IPC_SHM_RUNNING:
        time.sleep(random.uniform(0.8, 1.5))
        
        target_addr = random.randint(0, STATUS.shm_size - 1)
        # 生成两个随机大写字母作为数据
        new_data = ''.join(random.choices(string.ascii_uppercase, k=2))
        
        with STATUS._lock:
            STATUS.shm_data[target_addr] = new_data
            # 记录操作到操作列表用于前端高亮
            STATUS.shm_ops.append({
                'type': 'WRITE',
                'pid': name,
                'addr': target_addr,
                'val': new_data,
                'time': time.time()
            })
            # 保持操作列表不超过20个元素
            if len(STATUS.shm_ops) > 20:
                STATUS.shm_ops.pop(0)

def shm_reader_task(name="Reader"):
    """
    读进程：随机从共享内存读取数据
    """
    while IPC_SHM_RUNNING:
        time.sleep(random.uniform(0.5, 1.2)) # 读通常比写快
        
        target_addr = random.randint(0, STATUS.shm_size - 1)
        
        with STATUS._lock:
            data = STATUS.shm_data[target_addr]
            # 记录操作到操作列表用于前端高亮
            STATUS.shm_ops.append({
                'type': 'READ',
                'pid': name,
                'addr': target_addr,
                'val': data,
                'time': time.time()
            })
            # 保持操作列表不超过20个元素
            if len(STATUS.shm_ops) > 20:
                STATUS.shm_ops.pop(0)


# === 控制函数 ===

def start_ipc_simulation():
    """
    启动 IPC 机制演示：创建生产者和消费者线程。
    """
    global IPC_RUNNING
    IPC_RUNNING = True
    
    # 使用 utils_concurrency.py 中的函数来启动线程
    producer_thread = start_simulation_thread(producer_task, args=("P1",))
    consumer_thread = start_simulation_thread(consumer_task, args=("C1",))

    # 返回线程对象，方便管理
    return [producer_thread, consumer_thread]


def stop_ipc_simulation():
    """
    停止 IPC 机制演示：设置全局标志让线程退出。
    """
    global IPC_RUNNING
    IPC_RUNNING = False
    print("IPC simulation stopped.")

def start_shm_simulation():
    """启动共享内存模拟 (新增)"""
    global IPC_SHM_RUNNING
    IPC_SHM_RUNNING = True
    # 启动 1 个写者，2 个读者
    t1 = start_simulation_thread(shm_writer_task, args=("Writer-A",))
    t2 = start_simulation_thread(shm_reader_task, args=("Reader-1",))
    t3 = start_simulation_thread(shm_reader_task, args=("Reader-2",))
    return [t1, t2, t3]

def stop_shm_simulation():
    """停止共享内存模拟 (新增)"""
    global IPC_SHM_RUNNING
    IPC_SHM_RUNNING = False