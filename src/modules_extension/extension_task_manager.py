# src/modules_extension/extension_task_manager.py
# 任务管理器数据汇总与资源模拟

import psutil  # 用于获取真实系统信息
import random
from typing import Dict, List, Any
# 修正: 导入正确的全局状态实例
from src.system_status import STATUS

# 假设 config.py 存在
try:
    from config import NUM_CPUS, MEMORY_SIZE
except ImportError:
    NUM_CPUS = 4
    MEMORY_SIZE = 4096


# --- 辅助函数 (保持简洁，主要用于获取系统资源) ---

def get_cpu_utilization() -> float:
    """获取 CPU 利用率 (使用 psutil 真实数据)"""
    try:
        # 尝试获取真实的 CPU 利用率
        return psutil.cpu_percent(interval=None, percpu=False)
    except Exception:
        # 失败时返回模拟值
        return random.uniform(10.0, 50.0)


def get_memory_status() -> Dict[str, float]:
    """获取内存状态 (使用 psutil 真实数据)"""
    try:
        mem = psutil.virtual_memory()
        total_mb = round(mem.total / (1024 * 1024), 1)
        used_mb = round(mem.used / (1024 * 1024), 1)
    except Exception:
        # 失败时返回模拟值
        total_mb = MEMORY_SIZE
        used_mb = random.uniform(50.0, total_mb / 2)

    return {
        "memory_total_mb": total_mb,
        "memory_used_mb": used_mb,
    }


# --- 聚合函数 (供 MainWindow 调用) ---

def get_system_metrics() -> Dict[str, Any]:
    """
    聚合 CPU 和内存指标，供 MainWindow 使用。
    修复 main_window.py 中对 system.get_system_metrics() 的调用。
    """
    cpu_util = get_cpu_utilization()
    mem_status = get_memory_status()

    return {
        "cpu_usage": round(cpu_util, 1),
        "used_memory": round(mem_status["memory_used_mb"], 1),
        "total_memory": round(mem_status["memory_total_mb"], 1),
    }

# 可以在此添加 get_process_list_data 等函数，但此处仅提供核心修复