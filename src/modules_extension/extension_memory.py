# src/modules_extension/extension_memory.py
#动态内存分配与页面置换算法

from config import MEMORY_SIZE, PAGE_SIZE
from src.system_status import SystemStatus
from typing import List, Dict, Tuple
import random

STATUS = SystemStatus()
# 内存块状态定义：(start_addr, size, is_allocated, pid)
MemoryBlock = Tuple[int, int, bool, int]

# 页面访问记录
class PageAccessRecord:
    def __init__(self, pid: int, page_id: int, access_time: float):
        self.pid = pid
        self.page_id = page_id
        self.access_time = access_time

# 页面置换算法类型
def initialize_memory():
    """
    初始化内存：创建一个巨大的空闲块。
    """
    with STATUS._lock:
        # 重置内存布局，假设起始地址为 0
        STATUS.memory_layout = [(0, MEMORY_SIZE, False, -1)]
        STATUS.page_table = {}
        STATUS.next_free_frame = 0
        STATUS.page_access_history = []
        STATUS.page_fault_count = 0
        STATUS.page_hit_count = 0
        print(f"Memory initialized. Total size: {MEMORY_SIZE} MB.")


def first_fit_allocate(pid: int, required_size: int) -> bool:
    """
    动态内存分配算法：First Fit (首次适应)。
    尝试找到第一个足够大的空闲块进行分配。
    """
    with STATUS._lock:
        new_layout: List[MemoryBlock] = []
        allocated = False

        for i, (start, size, is_alloc, block_pid) in enumerate(STATUS.memory_layout):
            if not is_alloc and size >= required_size and not allocated:
                # 找到第一个合适的空闲块

                # 1. 分配：创建一个新的已分配块
                new_layout.append((start, required_size, True, pid))

                # 2. 剩余部分：如果还有剩余，创建一个新的空闲块
                remaining_size = size - required_size
                if remaining_size > 0:
                    new_layout.append((start + required_size, remaining_size, False, -1))

                allocated = True
                print(f"PID {pid} allocated {required_size}MB using First Fit at address {start}.")

            else:
                # 保持原有的块不变
                new_layout.append((start, size, is_alloc, block_pid))

        # 更新全局内存状态
        STATUS.memory_layout = new_layout
        return allocated


def best_fit_allocate(pid: int, required_size: int) -> bool:
    """
    动态内存分配算法：Best Fit (最佳适应)。
    尝试找到最小的足够大的空闲块进行分配。
    """
    with STATUS._lock:
        best_block_index = -1
        best_block_size = float('inf')
        new_layout: List[MemoryBlock] = list(STATUS.memory_layout)
        allocated = False

        # 找到最佳的空闲块
        for i, (start, size, is_alloc, block_pid) in enumerate(STATUS.memory_layout):
            if not is_alloc and size >= required_size and size < best_block_size:
                best_block_index = i
                best_block_size = size

        if best_block_index != -1:
            start, size, is_alloc, block_pid = STATUS.memory_layout[best_block_index]
            new_layout.pop(best_block_index)
            
            # 1. 分配：创建一个新的已分配块
            new_layout.append((start, required_size, True, pid))
            
            # 2. 剩余部分：如果还有剩余，创建一个新的空闲块
            remaining_size = size - required_size
            if remaining_size > 0:
                new_layout.append((start + required_size, remaining_size, False, -1))
            
            # 按起始地址排序内存块
            new_layout.sort(key=lambda x: x[0])
            
            allocated = True
            print(f"PID {pid} allocated {required_size}MB using Best Fit at address {start}.")

        # 更新全局内存状态
        STATUS.memory_layout = new_layout
        return allocated


def worst_fit_allocate(pid: int, required_size: int) -> bool:
    """
    动态内存分配算法：Worst Fit (最坏适应)。
    尝试找到最大的空闲块进行分配。
    """
    with STATUS._lock:
        worst_block_index = -1
        worst_block_size = -1
        new_layout: List[MemoryBlock] = list(STATUS.memory_layout)
        allocated = False

        # 找到最坏的空闲块
        for i, (start, size, is_alloc, block_pid) in enumerate(STATUS.memory_layout):
            if not is_alloc and size >= required_size and size > worst_block_size:
                worst_block_index = i
                worst_block_size = size

        if worst_block_index != -1:
            start, size, is_alloc, block_pid = STATUS.memory_layout[worst_block_index]
            new_layout.pop(worst_block_index)
            
            # 1. 分配：创建一个新的已分配块
            new_layout.append((start, required_size, True, pid))
            
            # 2. 剩余部分：如果还有剩余，创建一个新的空闲块
            remaining_size = size - required_size
            if remaining_size > 0:
                new_layout.append((start + required_size, remaining_size, False, -1))
            
            # 按起始地址排序内存块
            new_layout.sort(key=lambda x: x[0])
            
            allocated = True
            print(f"PID {pid} allocated {required_size}MB using Worst Fit at address {start}.")

        # 更新全局内存状态
        STATUS.memory_layout = new_layout
        return allocated


def deallocate_memory(pid: int):
    """
    内存回收：释放指定 PID 的所有内存块，并尝试进行块合并。
    """
    with STATUS._lock:
        # 1. 释放所有属于该 PID 的块
        current_layout = list(STATUS.memory_layout)
        for i, (start, size, is_alloc, block_pid) in enumerate(current_layout):
            if is_alloc and block_pid == pid:
                current_layout[i] = (start, size, False, -1)  # 设置为未分配

        # 2. 合并相邻的空闲块
        merged_layout: List[MemoryBlock] = []
        i = 0
        while i < len(current_layout):
            start, size, is_alloc, block_pid = current_layout[i]
            if not is_alloc:
                # 尝试合并后续的空闲块
                j = i + 1
                while j < len(current_layout) and not current_layout[j][2]:
                    size += current_layout[j][1]
                    j += 1
                merged_layout.append((start, size, False, -1))
                i = j
            else:
                merged_layout.append((start, size, is_alloc, block_pid))
                i += 1

        STATUS.memory_layout = merged_layout
        print(f"PID {pid} memory deallocated.")


# --- 页面置换模拟 ---

# 模拟页表结构 {page_id: (frame_id, last_accessed_time)}
PAGE_FRAMES = MEMORY_SIZE // PAGE_SIZE  # 总物理页框数


def access_page(page_id: int, algorithm: str = "LRU"):
    """
    模拟进程访问一个逻辑页，并触发页面置换。
    """
    # 使用一个全局的页框字典来模拟物理内存
    global_frames = STATUS.page_table
    current_time = STATUS.global_timer  # 使用系统时钟模拟访问时间
    pid = 0  # 简化版，使用单一进程
    page_key = (pid, page_id)

    with STATUS._lock:
        # 记录页面访问
        STATUS.page_access_history.append(PageAccessRecord(pid, page_id, current_time))

        if page_key in global_frames:
            # 命中 (Hit)
            global_frames[page_key] = (global_frames[page_key][0], current_time)
            STATUS.page_hit_count += 1
            print(f"Page Hit: PID {pid}, Page {page_id}. Updated access time.")
            return False, None  # 返回 (是否缺页, 被替换的页面)

        else:
            # 缺页 (Miss)：需要分配页框或进行置换
            STATUS.page_fault_count += 1
            print(f"Page Fault: PID {pid}, Page {page_id}. Starting replacement...")

            replaced_page = None
            if len(global_frames) < PAGE_FRAMES:
                # 还有空闲页框：直接分配
                new_frame_id = STATUS.next_free_frame
                global_frames[page_key] = (new_frame_id, current_time)
                STATUS.next_free_frame += 1
                print(f"Allocated new frame {new_frame_id}.")

            else:
                # 页面置换
                if algorithm == "FIFO":
                    # FIFO: 找到最早分配的页进行置换
                    oldest_page_key = min(global_frames.keys(), key=lambda k: global_frames[k][1])
                elif algorithm == "LRU":
                    # LRU: 找到最近最少使用的页进行置换
                    lru_page_key = min(global_frames.keys(), key=lambda k: global_frames[k][1])
                    oldest_page_key = lru_page_key
                elif algorithm == "OPT":
                    # OPT: 找到未来最长时间不使用的页进行置换
                    oldest_page_key = _optimal_page_replacement(global_frames, pid, page_id)
                else:
                    # 默认使用LRU
                    lru_page_key = min(global_frames.keys(), key=lambda k: global_frames[k][1])
                    oldest_page_key = lru_page_key
                
                replaced_page = oldest_page_key[1]  # 获取被替换的页面号
                lru_frame_id = global_frames[oldest_page_key][0]

                # 执行置换
                del global_frames[oldest_page_key]
                global_frames[page_key] = (lru_frame_id, current_time)

                print(f"{algorithm} Replacement: Replaced {oldest_page_key} with {page_key} in frame {lru_frame_id}.")

            return True, replaced_page  # 返回 (是否缺页, 被替换的页面)


def _optimal_page_replacement(global_frames: Dict, current_pid: int, current_page: int) -> Tuple[int, int]:
    """
    OPT页面置换算法：预测未来访问情况
    """
    # 简化版：假设未来访问是随机的，选择一个随机页面进行置换
    # 实际实现中，应该分析未来的页面访问序列
    return random.choice(list(global_frames.keys()))


def get_memory_stats():
    """
    获取内存使用统计信息
    """
    with STATUS._lock:
        total_memory = MEMORY_SIZE
        used_memory = 0
        free_memory = 0
        free_blocks = 0
        allocated_blocks = 0
        
        for (start, size, is_alloc, pid) in STATUS.memory_layout:
            if is_alloc:
                used_memory += size
                allocated_blocks += 1
            else:
                free_memory += size
                free_blocks += 1
        
        # 计算页面访问统计
        total_accesses = STATUS.page_hit_count + STATUS.page_fault_count
        hit_rate = STATUS.page_hit_count / total_accesses if total_accesses > 0 else 0
        fault_rate = STATUS.page_fault_count / total_accesses if total_accesses > 0 else 0
        
        return {
            "total_memory": total_memory,
            "used_memory": used_memory,
            "free_memory": free_memory,
            "free_blocks": free_blocks,
            "allocated_blocks": allocated_blocks,
            "page_frames": PAGE_FRAMES,
            "used_frames": len(STATUS.page_table),
            "free_frames": PAGE_FRAMES - len(STATUS.page_table),
            "page_hits": STATUS.page_hit_count,
            "page_faults": STATUS.page_fault_count,
            "total_accesses": total_accesses,
            "hit_rate": hit_rate,
            "fault_rate": fault_rate
        }

# 添加缺失的函数

def initialize_page_table(total_frames: int):
    """
    初始化页表和物理页框
    """
    with STATUS._lock:
        STATUS.page_table = {}
        STATUS.next_free_frame = 0
        STATUS.page_access_history = []
        STATUS.page_fault_count = 0
        STATUS.page_hit_count = 0
        print(f"Page table initialized with {total_frames} frames.")


def get_page_table_status():
    """
    获取页表和物理页框的状态
    """
    with STATUS._lock:
        page_table = {}
        physical_frames = []
        
        # 转换页表格式：{page_number: (frame_number, is_valid, last_accessed)}
        for (pid, page_id), (frame_id, last_accessed) in STATUS.page_table.items():
            page_table[page_id] = (frame_id, True, last_accessed)
        
        # 转换物理页框格式：[(page_number, is_occupied)]
        for frame_id in range(PAGE_FRAMES):
            page_number = None
            is_occupied = False
            for (pid, page_id), (frame, _) in STATUS.page_table.items():
                if frame == frame_id:
                    page_number = page_id
                    is_occupied = True
                    break
            physical_frames.append((page_number, is_occupied))
        
        return page_table, physical_frames


def get_page_access_history():
    """
    获取页面访问历史
    """
    with STATUS._lock:
        return [record.page_id for record in STATUS.page_access_history]


def reset_memory():
    """
    重置所有内存，回收所有已分配的内存块
    """
    with STATUS._lock:
        # 清空内存布局，只保留一个完整的空闲块
        STATUS.memory_layout = [(0, MEMORY_SIZE, False, -1)]
        print(f"All memory has been reset. Total memory: {MEMORY_SIZE} MB")

# 示例：
# initialize_memory()
# first_fit_allocate(101, 100)
# access_page(101, 1)