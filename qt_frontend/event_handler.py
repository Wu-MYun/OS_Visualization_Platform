# qt_frontend/event_handler.py (完整代码)
# 负责GUI事件分发、前后端数据同步

from PyQt6.QtWidgets import QMessageBox
from src.system_status import STATUS
from src.process_model import Process, ProcessState
from src.modules_core.module_1_process_state import generate_initial_processes, transition_state
from src.modules_core.module_2_ipc import start_ipc_simulation
# 修正 1: 导入调度器管理器
from src.modules_core.module_4_multicore_scheduler import SCHEDULER_MANAGER
from src.modules_extension.extension_rtos import start_rtos_simulation as rtos_start


class EventHandler:
    def __init__(self, main_window):
        self.main_window = main_window  # 主窗口实例
        # 新增：记录当前选择的算法
        self.current_algorithm = 'FCFS'

    def set_algorithm(self, algorithm: str):
        """设置当前调度算法"""
        self.current_algorithm = algorithm
        self.main_window.status_bar.showMessage(f"已选择调度算法: {algorithm}", 3000)

    def create_test_processes(self):
        """处理 '生成测试进程' 按钮点击事件"""

        # 调用核心模块初始化进程（创建 10 个新进程）
        new_processes = generate_initial_processes(count=10)

        if new_processes:
            self.main_window.status_bar.showMessage(
                f"已创建 {len(new_processes)} 个新进程，PID 范围: {new_processes[0].pid}-{new_processes[-1].pid}。", 3000)
        else:
            self.main_window.status_bar.showMessage("未创建新进程。", 3000)

        # 立即触发一次 UI 刷新
        self.main_window.update_process_status()
        
    def create_single_process(self):
        """处理 '新建单个进程' 按钮点击事件"""

        # 调用核心模块初始化进程（创建 1 个新进程）
        new_processes = generate_initial_processes(count=1)

        if new_processes:
            self.main_window.status_bar.showMessage(
                f"已创建 1 个新进程，PID: {new_processes[0].pid}。", 3000)
        else:
            self.main_window.status_bar.showMessage("未创建新进程。", 3000)

        # 立即触发一次 UI 刷新
        self.main_window.update_process_status()

    def start_simulation(self):
        """处理 '启动模拟/调度' 按钮点击事件"""

        if STATUS.scheduler_running:
            QMessageBox.warning(self.main_window, "警告", "模拟器已在运行。")
            return

        # 1. 自动创建初始进程
        if not STATUS.all_processes:
            generate_initial_processes(count=5)

        # 2. 启动调度器线程，传入当前选择的算法
        SCHEDULER_MANAGER.start_schedulers(algorithm=self.current_algorithm)

        self.main_window.status_bar.showMessage(f"调度器模拟已启动！(算法: {self.current_algorithm})", 3000)
        self.main_window.update_process_status()

    def stop_all_simulations(self):
        """停止所有模拟线程和定时器"""

        # 关键: 停止调度器线程
        SCHEDULER_MANAGER.stop_schedulers()

        self.main_window.update_process_status()  # 刷新UI清空表格
        self.main_window.status_bar.showMessage("所有模拟已停止并重置数据。", 3000)

    def close_application(self):
        """关闭应用程序"""
        self.stop_all_simulations()
        self.main_window.close()

    def start_ipc_simulation(self):
        """启动IPC模拟"""
        # 直接控制Qt界面的可视化系统
        if hasattr(self.main_window, 'ipc_visualization'):
            if not self.main_window.ipc_visualization.simulation_running:
                self.main_window.ipc_visualization.toggle_simulation()
                # 更新状态显示
                self.main_window.status_bar.showMessage("IPC模拟已启动！", 3000)
    
    def stop_ipc_simulation(self):
        """停止IPC模拟"""
        # 直接控制Qt界面的可视化系统
        if hasattr(self.main_window, 'ipc_visualization'):
            if self.main_window.ipc_visualization.simulation_running:
                self.main_window.ipc_visualization.toggle_simulation()
                # 更新状态显示
                self.main_window.status_bar.showMessage("IPC模拟已停止！", 3000)
    
    def reset_ipc_simulation(self):
        """重置IPC模拟"""
        # 直接控制Qt界面的可视化系统
        if hasattr(self.main_window, 'ipc_visualization'):
            self.main_window.ipc_visualization.reset_simulation()
            # 更新状态显示
            self.main_window.status_bar.showMessage("IPC模拟已重置！", 3000)
    
    def start_shm_simulation(self):
        """启动共享内存模拟"""
        # 直接控制Qt界面的可视化系统
        if hasattr(self.main_window, 'shm_visualization'):
            if not self.main_window.shm_visualization.simulation_running:
                self.main_window.shm_visualization.toggle_simulation()
                # 更新状态显示
                self.main_window.status_bar.showMessage("共享内存模拟已启动！", 3000)
    
    def stop_shm_simulation(self):
        """停止共享内存模拟"""
        # 直接控制Qt界面的可视化系统
        if hasattr(self.main_window, 'shm_visualization'):
            if self.main_window.shm_visualization.simulation_running:
                self.main_window.shm_visualization.toggle_simulation()
                # 更新状态显示
                self.main_window.status_bar.showMessage("共享内存模拟已停止！", 3000)

    def start_rtos_simulation(self):
        """启动RTOS模拟"""
        if STATUS.rtos_running:
            self.main_window.status_bar.showMessage("RTOS模拟已在运行！", 3000)
            return
        
        # 启动RTOS模拟
        rtos_start()
        self.main_window.status_bar.showMessage("RTOS模拟已启动！", 3000)

    def stop_rtos_simulation(self):
        """停止RTOS模拟"""
        STATUS.rtos_running = False
        self.main_window.status_bar.showMessage("RTOS模拟已停止！", 3000)

    def reset_rtos_simulation(self):
        """重置RTOS模拟"""
        self.stop_rtos_simulation()
        
        # 完全重置RTOS状态
        with STATUS._lock:
            STATUS.all_processes.clear()
            STATUS.rtos_timeline.clear()
            STATUS.global_timer = 0
        
        # 重置全局中断标志
        import src.modules_extension.extension_rtos as rtos_module
        rtos_module.pending_isr = None
        
        # 更新UI
        if hasattr(self.main_window, 'rtos_timeline'):
            self.main_window.rtos_timeline.reset_simulation()
            
        self.main_window.status_bar.showMessage("RTOS模拟已重置！", 3000)

    # --- 状态变化与控制 ---

    def handle_process_state_change(self, process: Process):
        """处理进程状态变化事件：同步更新UI+弹窗提示（可选）"""
        self.main_window.update_process_status()
        # 状态变化频繁时，建议注释掉 QMessageBox，避免干扰
        # QMessageBox.information(
        #     self.main_window,
        #     "进程状态变化",
        #     f"进程{process.pid}状态已更新为: {process.state.value}"
        # )
        pass

    def handle_pause_process(self, pid: int):
        # 使用 STATUS 获取进程，并转换为 BLOCKED 状态
        process = STATUS.all_processes.get(pid)
        if process and process.state != ProcessState.TERMINATED:
            transition_state(process, ProcessState.BLOCKED)
            self.main_window.status_bar.showMessage(f"进程 PID {pid} 已暂停(BLOCKED)。", 3000)
            self.main_window.update_process_status()