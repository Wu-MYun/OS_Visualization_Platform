# config.py
#全局配置

# === CPU 调度模块配置 (对应 模块 4 & 扩展 3) ===
NUM_CPUS = 4            # 模拟的 CPU 核心数 (实现多核调度)
TIME_SLICE = 2          # 时间片轮转 (RR) 算法的时间片大小
MAX_PROCESS_COUNT = 20  # 最大进程数量

# === 内存管理模块配置 (对应 扩展 2) ===
MEMORY_SIZE = 1024      # 模拟的总内存大小 (MB)
PAGE_SIZE = 4           # 页面大小 (KB/MB)

# === RTOS 模块配置 (对应 扩展 4) ===
RTOS_PRIORITY_RANGE = (1, 10)  # RTOS 任务的优先级范围 (1最高)

# === 任务管理器刷新频率 (对应 扩展 1) ===
REFRESH_INTERVAL_MS = 100  # 任务管理器数据刷新间隔 (毫秒) - 降低到100ms以提高RTOS时间线的流畅度