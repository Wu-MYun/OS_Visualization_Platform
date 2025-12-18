# qt_frontend/main_window.py
# 主窗口类：集成甘特图、状态图和控制面板 (Final Version)

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton, QStatusBar,
    QGridLayout, QHeaderView, QGroupBox, QComboBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from collections import defaultdict

from src.system_status import STATUS
from src.process_model import ProcessState
from qt_frontend.event_handler import EventHandler
from src.modules_core.module_4_multicore_scheduler import SCHEDULER_MANAGER
from config import REFRESH_INTERVAL_MS, NUM_CPUS

from qt_frontend.visuals.qt_gantt_chart import QtGanttChart
from qt_frontend.visuals.qt_process_states import QtProcessStates
# 注意：这里导入了新的 QtSharedMemoryVisualization 类
from qt_frontend.visuals.qt_ipc_visualization import QtIpcVisualization, QtSharedMemoryVisualization
from qt_frontend.visuals.qt_semaphore_visualization import QtSemaphoreVisualization
from qt_frontend.visuals.qt_memory_allocation import QtMemoryAllocation
from qt_frontend.visuals.qt_page_replacement import QtPageReplacement
from qt_frontend.visuals.qt_rtos_timeline import QtRTOSimeline

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("操作系统可视化实验平台")
        self.setGeometry(100, 100, 1400, 850) 

        self.event_handler = EventHandler(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # === 顶部：选项卡 ===
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #C2C7CB; background: white; }
            QTabBar::tab { height: 35px; width: 160px; font-weight: bold; }
        """)
        
        self.init_process_tab()
        self.init_state_diagram_tab()
        self.init_scheduler_tab()
        self.init_ipc_tab() # 这里会调用修改后的初始化函数
        self.init_semaphore_tab()
        self.init_memory_allocation_tab()
        self.init_page_replacement_tab()
        self.init_rtos_tab()

        main_layout.addWidget(self.tab_widget)

        # 创建一个共享的控制台实例
        self.shared_control_panel = self.init_control_panel()
        # 默认先不添加到布局中

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.setup_connections()
        
        # 设置初始算法
        self.algorithm_selector.setCurrentText("FCFS")
        
        # 🌟 自动初始化：100ms后自动生成10个进程，无需用户点击
        QTimer.singleShot(100, self.auto_init_processes)
        
        # 连接选项卡切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # 初始显示第一个选项卡的控制台
        self.on_tab_changed(0)

    def auto_init_processes(self):
        print("System Auto-Init: Generating 10 processes...")
        self.event_handler.create_test_processes()
        self.update_process_status()

    def init_process_tab(self):
        self.process_page = QWidget()
        layout = QVBoxLayout(self.process_page)
        
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(7)
        self.process_table.setHorizontalHeaderLabels([
            "PID", "状态", "到达时间", "总需时间", "剩余时间", "优先级", "等待时间"
        ])
        self.process_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.process_table.setAlternatingRowColors(True)
        self.process_table.setStyleSheet("QTableWidget { selection-background-color: #D6EAF8; selection-color: black; }")
        layout.addWidget(self.process_table)
        
        # 保存布局引用，用于动态添加/移除控制台
        self.process_tab_layout = layout
        
        self.tab_widget.addTab(self.process_page, "列表视图 (List View)")

    def init_state_diagram_tab(self):
        # 创建一个容器布局，同时包含状态图和控制台
        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        
        # 添加状态图
        self.state_page = QtProcessStates()
        container_layout.addWidget(self.state_page)
        
        # 保存布局引用，用于动态添加/移除控制台
        self.state_tab_layout = container_layout
        
        self.tab_widget.addTab(container_widget, "状态转换图")

    def init_scheduler_tab(self):
        self.scheduler_page = QWidget()
        main_layout = QVBoxLayout(self.scheduler_page)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 1. 上部：甘特图和分析报告并排
        upper_layout = QHBoxLayout()
        upper_layout.setSpacing(10)
        
        # 左侧：甘特图
        self.gantt_chart = QtGanttChart(num_cpus=NUM_CPUS)
        self.gantt_chart.setMinimumHeight(550)  # 增加甘特图高度，使其更长
        upper_layout.addWidget(self.gantt_chart, 3)  # 增加甘特图的权重比例
        
        # 右侧：实时调度分析报告
        analysis_group = QGroupBox("实时调度分析报告")
        analysis_layout = QVBoxLayout(analysis_group)
        analysis_layout.setSpacing(5)
        analysis_group.setMaximumWidth(350)  # 保持分析报告的宽度
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setStyleSheet("background-color: #FDFEFE; font-family: Consolas; font-size: 9.5pt; border: 1px solid #E0E0E0; border-radius: 3px;")  # 增大字体大小
        self.analysis_text.setMinimumHeight(530)  # 保持分析文本框高度
        analysis_layout.addWidget(self.analysis_text)
        
        upper_layout.addWidget(analysis_group, 1)  # 保持分析报告的权重
        
        main_layout.addLayout(upper_layout)
        
        # 2. 下部：关键性能指标横向排列
        metrics_group = QGroupBox("关键性能指标")
        metrics_layout = QHBoxLayout(metrics_group)
        metrics_layout.setSpacing(10)  # 设置合适的间距
        metrics_layout.setContentsMargins(8, 5, 8, 5)  # 保持内边距
        
        self.metric_cpu = QLabel("CPU 利用率\n0.0%")
        self.metric_wait = QLabel("平均等待\n0.00s")
        self.metric_turnaround = QLabel("平均周转\n0.00s")
        
        for lbl in [self.metric_cpu, self.metric_wait, self.metric_turnaround]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; font-size: 9pt; border: 1px solid #E0E0E0; padding: 8px 12px; border-radius: 4px; margin: 1px;")  # 调整内边距，使框与字体比例协调
            lbl.setMinimumWidth(150)  # 设置相同的最小宽度
            lbl.setFixedHeight(60)  # 设置固定高度，确保三个框高度一致
            metrics_layout.addWidget(lbl)
        
        main_layout.addWidget(metrics_group)

        # 保存布局引用，用于动态添加/移除控制台
        self.scheduler_tab_layout = main_layout

        self.tab_widget.addTab(self.scheduler_page, "调度甘特图与分析")

    def init_control_panel(self):
        panel = QGroupBox("控制台")
        panel.setMaximumHeight(100)
        layout = QHBoxLayout(panel)

        layout.addWidget(QLabel("调度算法:"))
        self.algorithm_selector = QComboBox()
        self.algorithm_selector.addItems(['FCFS', 'RR', 'Priority', 'SJF'])
        self.algorithm_selector.setMinimumWidth(150)
        layout.addWidget(self.algorithm_selector)

        layout.addStretch(1)

        self.lbl_timer = QLabel("系统时间: 0.0s")
        self.lbl_queues = QLabel("就绪: 0 | 阻塞: 0")
        self.lbl_timer.setStyleSheet("font-weight: bold; color: #2E86C1;")
        layout.addWidget(self.lbl_timer)
        layout.addSpacing(20)
        layout.addWidget(self.lbl_queues)

        layout.addStretch(1)

        self.btn_create = QPushButton("新建单个进程")
        self.btn_start = QPushButton("启动模拟")
        self.btn_stop = QPushButton("停止 / 重置")
        
        self.btn_create.setStyleSheet("background-color: #5D6D7E; color: white; padding: 5px 15px;")
        self.btn_start.setStyleSheet("background-color: #27AE60; color: white; padding: 5px 15px; font-weight: bold;")
        self.btn_stop.setStyleSheet("background-color: #C0392B; color: white; padding: 5px 15px;")

        layout.addWidget(self.btn_create)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)

        return panel

    def setup_connections(self):
        # 修正：当算法选择改变时，通知 SchedulerManager 更新算法
        self.algorithm_selector.currentTextChanged.connect(
            lambda algo: SCHEDULER_MANAGER.update_algorithm(algo)
        )
        self.algorithm_selector.currentTextChanged.connect(self.event_handler.set_algorithm)
        
        self.btn_create.clicked.connect(self.event_handler.create_single_process)
        self.btn_start.clicked.connect(self.event_handler.start_simulation)
        self.btn_stop.clicked.connect(self.event_handler.stop_all_simulations)
        
        # IPC: 消息队列连接
        self.start_ipc_button.clicked.connect(self.event_handler.start_ipc_simulation)
        self.stop_ipc_button.clicked.connect(self.event_handler.stop_ipc_simulation)
        self.reset_ipc_button.clicked.connect(self.event_handler.reset_ipc_simulation)
        
        # IPC: 共享内存连接 (新增)
        self.start_shm_button.clicked.connect(self.event_handler.start_shm_simulation)
        self.stop_shm_button.clicked.connect(self.event_handler.stop_shm_simulation)
        
        # RTOS 模拟按钮连接
        self.start_rtos_button.clicked.connect(self.event_handler.start_rtos_simulation)
        self.stop_rtos_button.clicked.connect(self.event_handler.stop_rtos_simulation)
        self.reset_rtos_button.clicked.connect(self.event_handler.reset_rtos_simulation)

        self.timer = QTimer(self)
        self.timer.setInterval(REFRESH_INTERVAL_MS)
        self.timer.timeout.connect(self.update_process_status)
        self.timer.start()

    def on_tab_changed(self, index):
        """选项卡切换时更新系统状态显示并动态显示/隐藏控制台"""
        tab_text = self.tab_widget.tabText(index)
        self.status_bar.showMessage(f"当前页面: {tab_text}")
        
        # 先从所有布局中移除控制台
        if self.shared_control_panel.parent():
            self.shared_control_panel.parent().layout().removeWidget(self.shared_control_panel)
        
        # 只在前三个选项卡显示控制台
        if index == 0:  # 列表视图
            self.process_tab_layout.addWidget(self.shared_control_panel)
        elif index == 1:  # 状态转换图
            self.state_tab_layout.addWidget(self.shared_control_panel)
        elif index == 2:  # 调度甘特图与分析
            self.scheduler_tab_layout.addWidget(self.shared_control_panel)

    def init_ipc_tab(self):
        """初始化进程间通信(IPC)选项卡 - 修改版：支持多种IPC模式"""
        self.ipc_page = QWidget()
        main_layout = QVBoxLayout(self.ipc_page)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 创建内部的 TabWidget 用于切换不同的通信方式
        # ！！！这是界面变化的关键，必须有这个 QTabWidget ！！！
        self.ipc_sub_tabs = QTabWidget()
        
        # 设置选项卡宽度策略，确保文本完全显示 (需在addTab前设置)
        self.ipc_sub_tabs.setTabBarAutoHide(False)
        self.ipc_sub_tabs.tabBar().setExpanding(True)
        
        # === 1. 消息队列 (现有功能) ===
        self.msg_queue_tab = QWidget()
        msg_layout = QVBoxLayout(self.msg_queue_tab)
        
        # 消息队列可视化组件
        self.ipc_visualization = QtIpcVisualization()
        self.ipc_visualization.setMinimumHeight(350)
        msg_layout.addWidget(self.ipc_visualization)
        
        # 消息队列日志
        self.queue_status = QTextEdit()
        self.queue_status.setReadOnly(True)
        self.queue_status.setMaximumHeight(100)
        self.queue_status.setPlaceholderText("消息队列日志将显示在这里...")
        msg_layout.addWidget(self.queue_status)
        
        # 消息队列控制按钮
        msg_control_layout = QHBoxLayout()
        self.start_ipc_button = QPushButton("启动消息队列模拟")
        self.stop_ipc_button = QPushButton("停止")
        self.reset_ipc_button = QPushButton("重置")
        
        # 样式
        for btn in [self.start_ipc_button, self.stop_ipc_button, self.reset_ipc_button]:
            btn.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        self.start_ipc_button.setStyleSheet("background-color: #27AE60; color: white;")
        self.stop_ipc_button.setStyleSheet("background-color: #E67E22; color: white;")
        
        msg_control_layout.addWidget(self.start_ipc_button)
        msg_control_layout.addWidget(self.stop_ipc_button)
        msg_control_layout.addWidget(self.reset_ipc_button)
        msg_layout.addLayout(msg_control_layout)
        
        self.ipc_sub_tabs.addTab(self.msg_queue_tab, "消息队列")

        # === 2. 共享内存 (新增功能) ===
        self.shm_tab = QWidget()
        shm_layout = QVBoxLayout(self.shm_tab)
        
        # 共享内存可视化组件
        self.shm_visualization = QtSharedMemoryVisualization()
        shm_layout.addWidget(self.shm_visualization)
        
        # 共享内存日志/说明
        shm_info = QLabel("说明: 写进程随机向内存块写入两个字符，读进程随机读取。红色代表写入，蓝色代表读取。")
        shm_info.setStyleSheet("color: #64748b; font-style: italic; margin: 10px;")
        shm_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shm_layout.addWidget(shm_info)
        
        # 共享内存控制按钮
        shm_control_layout = QHBoxLayout()
        self.start_shm_button = QPushButton("启动共享内存模拟")
        self.stop_shm_button = QPushButton("停止")
        
        self.start_shm_button.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold; padding: 5px;")
        self.stop_shm_button.setStyleSheet("background-color: #E67E22; color: white; font-weight: bold; padding: 5px;")
        
        shm_control_layout.addWidget(self.start_shm_button)
        shm_control_layout.addWidget(self.stop_shm_button)
        shm_layout.addLayout(shm_control_layout)
        
        self.ipc_sub_tabs.addTab(self.shm_tab, "共享内存")
        
        main_layout.addWidget(self.ipc_sub_tabs)
        self.tab_widget.addTab(self.ipc_page, "进程间通信 (IPC)")
    
    def init_semaphore_tab(self):
        """初始化信号量同步机制选项卡"""
        # 实例化新的可视化类
        self.semaphore_page = QtSemaphoreVisualization()
        # 注意：这里我们不需要再手动布局，因为QtSemaphoreVisualization继承自QWidget且内部已经有了Layout
        self.tab_widget.addTab(self.semaphore_page, "信号量同步模型")
    
    def init_memory_allocation_tab(self):
        """初始化动态内存分配选项卡"""
        # 实例化新的可视化类
        self.memory_allocation_page = QtMemoryAllocation()
        self.tab_widget.addTab(self.memory_allocation_page, "动态内存分配")
    
    def init_page_replacement_tab(self):
        """初始化页面置换算法选项卡"""
        # 实例化新的可视化类
        self.page_replacement_page = QtPageReplacement()
        self.tab_widget.addTab(self.page_replacement_page, "页面置换算法")

    # ... 在 MainWindow 类中 ...
    
    def init_rtos_tab(self):
        """初始化RTOS任务切换可视化选项卡 (Pro 版集成)"""
        self.rtos_page = QWidget()
        main_layout = QVBoxLayout(self.rtos_page)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 1. 顶部全局控制栏 (启动/暂停/重置)
        control_bar = QWidget()
        control_layout = QHBoxLayout(control_bar)
        control_bar.setStyleSheet("background-color: #F0F0F0; border-bottom: 1px solid #DDD;")
        
        lbl = QLabel("RTOS 全局控制:")
        lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        # 定义按钮
        self.start_rtos_button = QPushButton("▶ 启动系统")
        self.start_rtos_button.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold;")
        
        self.stop_rtos_button = QPushButton("⏸ 暂停")
        self.stop_rtos_button.setStyleSheet("background-color: #E67E22; color: white; font-weight: bold;")
        
        self.reset_rtos_button = QPushButton("⏹ 重置")
        self.reset_rtos_button.setStyleSheet("background-color: #C0392B; color: white; font-weight: bold;")
        
        control_layout.addWidget(lbl)
        control_layout.addWidget(self.start_rtos_button)
        control_layout.addWidget(self.stop_rtos_button)
        control_layout.addWidget(self.reset_rtos_button)
        control_layout.addStretch()
        
        main_layout.addWidget(control_bar)

        # 2. 实例化核心仪表盘 (集成逻辑分析仪 + 寄存器 + TCB)
        # 注意：这里直接使用我们上一轮修改过的 QtRTOSimeline 类
        self.rtos_timeline = QtRTOSimeline()
        main_layout.addWidget(self.rtos_timeline)



        self.tab_widget.addTab(self.rtos_page, "RTOS 逻辑分析仪")

    def update_ipc_display(self):
        """更新IPC可视化显示"""
        with STATUS._lock:
            # 更新消息队列文字显示
            queue_content = "\n".join([f"[消息] {msg}" for msg in STATUS.message_queue])
            if not queue_content:
                queue_content = "[空队列]"
            self.queue_status.setPlainText(queue_content)
            
            # 使用动画组件更新可视化效果
            if hasattr(self, 'ipc_visualization'):
                self.ipc_visualization.update_visualization(STATUS.message_queue)
            
            # 共享内存部分通常由其自身的定时器更新，但如果需要同步可以在这里调用
            pass

    def update_process_status(self):
        try:
            with STATUS._lock:
                all_procs = list(STATUS.all_processes.values())
                
                # 1. 表格
                self.process_table.setRowCount(len(all_procs))
                finished_count = 0
                total_wait = 0
                total_turnaround = 0
                
                for idx, p in enumerate(all_procs):
                    self.process_table.setItem(idx, 0, QTableWidgetItem(str(p.pid)))
                    state_str = p.state.value
                    if p.state == ProcessState.RUNNING:
                        # 检查对象是否有cpu_id属性（避免RTOS_Task对象出现AttributeError）
                        if hasattr(p, 'cpu_id'):
                            state_str += f" (Core {p.cpu_id})"
                    self.process_table.setItem(idx, 1, QTableWidgetItem(state_str))
                    self.process_table.setItem(idx, 2, QTableWidgetItem(f"{p.arrival_time}"))
                    self.process_table.setItem(idx, 3, QTableWidgetItem(f"{p.burst_time}"))
                    self.process_table.setItem(idx, 4, QTableWidgetItem(f"{p.remaining_time:.1f}"))
                    self.process_table.setItem(idx, 5, QTableWidgetItem(str(p.priority)))
                    self.process_table.setItem(idx, 6, QTableWidgetItem(f"{p.wait_time:.1f}"))

                    if p.state == ProcessState.TERMINATED:
                        finished_count += 1
                        total_wait += p.wait_time
                        total_turnaround += p.turnaround_time
                        

                # 2. 状态图
                self.state_page.update_processes(all_procs)

                # 3. 甘特图与分析
                gantt_data = self._convert_cpu_history_to_gantt_data(STATUS.cpu_history, STATUS.global_timer)
                self.gantt_chart.update_schedule_data(gantt_data)
                
                self._update_analysis_report(finished_count, total_wait, total_turnaround, len(all_procs))
                
                self.lbl_timer.setText(f"系统时间: {STATUS.global_timer:.1f}s")
                self.lbl_queues.setText(f"就绪: {len(STATUS.ready_queue)} | 阻塞: {len(STATUS.blocked_queue)}")
        
                # 更新IPC显示
                self.update_ipc_display()

                # 更新RTOS时间轴
                if hasattr(self, 'rtos_timeline'):
                    self.rtos_timeline.update_timeline(STATUS.rtos_timeline)

                # === 新增：RTOS 实时刷新逻辑 ===
                # 只有当 RTOS 正在运行，且界面组件已创建时才更新
                if STATUS.rtos_running and hasattr(self, 'rtos_timeline'):
                    # 将最新的时间轴数据传递给组件，组件内部会自动分发给波形图和日志
                    self.rtos_timeline.update_timeline(STATUS.rtos_timeline)

        except Exception as e:
            print(f"Update Error: {e}")

    def _update_analysis_report(self, finished_count, total_wait, total_turnaround, total_procs):
        algo = self.algorithm_selector.currentText()
        avg_wait = total_wait / finished_count if finished_count > 0 else 0.0
        avg_turnaround = total_turnaround / finished_count if finished_count > 0 else 0.0
        
        # 计算更详细的性能指标
        active_cores = sum(1 for p in STATUS.running_processes.values() if p is not None)
        cpu_util = (active_cores / NUM_CPUS) * 100
        
        # 计算各状态进程数量
        state_counts = {}
        for state in ProcessState:
            state_counts[state] = sum(1 for p in STATUS.all_processes.values() if p.state == state)
        
        # 计算平均响应时间
        total_response = 0.0
        response_count = 0
        for p in STATUS.all_processes.values():
            if p.response_time is not None:
                total_response += p.response_time
                response_count += 1
        avg_response = total_response / response_count if response_count > 0 else 0.0
        
        # 更新性能指标面板
        self.metric_cpu.setText(f"CPU 利用率\n{cpu_util:.1f}%")
        self.metric_wait.setText(f"平均等待\n{avg_wait:.2f}s")
        self.metric_turnaround.setText(f"平均周转\n{avg_turnaround:.2f}s")
        
        # 确保三个指标使用相同的样式，保持大小一致
        for lbl in [self.metric_cpu, self.metric_wait, self.metric_turnaround]:
            lbl.setStyleSheet(f"font-weight: bold; font-size: 9pt; border: 1px solid #E0E0E0; padding: 8px 12px; border-radius: 4px; margin: 1px; background-color: {'#ABEBC6' if lbl is self.metric_cpu and cpu_util > 50 else '#F9E79F' if lbl is self.metric_cpu else '#FFFFFF'}; ")
            lbl.setMinimumWidth(150)
            lbl.setFixedHeight(60)

        # 生成详细的分析报告
        report = f"""
        <h3 style='color:#2E86C1; margin-bottom:5px;'>算法实时分析: {algo}</h3>
        
        <p><b>系统总体状态:</b></p>
        <ul>
            <li><b>时间:</b> {STATUS.global_timer:.1f}s</li>
            <li><b>进程总数:</b> {total_procs}个</li>
            <li><b>已完成:</b> {finished_count}个 ({(finished_count/total_procs*100 if total_procs > 0 else 0):.1f}%)</li>
            <li><b>就绪队列:</b> {len(STATUS.ready_queue)}个进程</li>
            <li><b>阻塞队列:</b> {len(STATUS.blocked_queue)}个进程</li>
        </ul>
        
        <p><b>进程状态分布:</b></p>
        <ul>
            <li><b>新建:</b> {state_counts.get(ProcessState.NEW, 0)}个</li>
            <li><b>就绪:</b> {state_counts.get(ProcessState.READY, 0)}个</li>
            <li><b>运行:</b> {state_counts.get(ProcessState.RUNNING, 0)}个</li>
            <li><b>阻塞:</b> {state_counts.get(ProcessState.BLOCKED, 0)}个</li>
            <li><b>终止:</b> {state_counts.get(ProcessState.TERMINATED, 0)}个</li>
        </ul>
        
        <p><b>性能指标:</b></p>
        <ul>
            <li><b>CPU利用率:</b> {cpu_util:.1f}%</li>
            <li><b>平均等待时间:</b> {avg_wait:.2f}s</li>
            <li><b>平均周转时间:</b> {avg_turnaround:.2f}s</li>
            <li><b>平均响应时间:</b> {avg_response:.2f}s</li>
        </ul>
        
        <p><b>算法特性分析:</b></p>
        <ul>
        """
        
        if algo == 'FCFS':
            report += "<li><b>公平性:</b> 严格按到达顺序，无饥饿风险。</li>"
            long_job_waiting = any(p.remaining_time > 10 and p.state == ProcessState.READY for p in STATUS.all_processes.values())
            if long_job_waiting:
                report += "<li style='color:red'><b>警报:</b> 检测到长作业等待，可能存在护航效应！</li>"
            elif cpu_util < 30:
                report += "<li style='color:orange'><b>注意:</b> CPU利用率较低，系统资源利用率不高。</li>"
            else:
                report += "<li><b>状态:</b> 队列流动正常，系统运行稳定。</li>"
        elif algo == 'RR':
            report += "<li><b>响应性:</b> 极佳。所有就绪进程轮流执行。</li>"
            report += "<li><b>开销:</b> 上下文切换频繁，适合交互式系统。</li>"
            if avg_wait > 5:
                report += "<li style='color:orange'><b>注意:</b> 平均等待时间较长，可能需要调整时间片大小。</li>"
        elif algo == 'Priority':
            report += "<li><b>优先级:</b> 高优先级先行，资源分配灵活。</li>"
            # 检查是否有饥饿风险
            low_prio_starving = any(p.priority > 5 and p.wait_time > 10 and p.state == ProcessState.READY for p in STATUS.all_processes.values())
            if low_prio_starving:
                report += "<li style='color:red'><b>警报:</b> 检测到低优先级进程可能存在饥饿！</li>"
            else:
                report += "<li><b>状态:</b> 进程调度符合优先级策略。</li>"
        elif algo == 'SJF':
            report += "<li><b>效率:</b> 理论等待时间最优，吞吐量高。</li>"
            report += "<li><b>局限性:</b> 可能导致长作业饥饿。</li>"
            long_job_starving = any(p.burst_time > 10 and p.wait_time > 15 and p.state == ProcessState.READY for p in STATUS.all_processes.values())
            if long_job_starving:
                report += "<li style='color:orange'><b>注意:</b> 检测到长作业可能存在饥饿风险。</li>"
        
        report += "</ul>"
        self.analysis_text.setHtml(report)

    def _convert_cpu_history_to_gantt_data(self, history, current_time):
        data = defaultdict(list)
        for cpu_id, events in history.items():
            start_t = 0
            curr_pid = -1
            sorted_events = sorted(events, key=lambda x: x['time'])
            
            for ev in sorted_events:
                t, pid, type_ = ev['time'], ev['pid'], ev['event']
                if curr_pid != -1 and t > start_t:
                    data[cpu_id].append({'pid': curr_pid, 'start': start_t, 'end': t})
                
                if type_ == "RUNNING":
                    curr_pid = pid
                    start_t = t
                else:
                    curr_pid = -1
                    start_t = t
            
            if curr_pid != -1 and current_time > start_t:
                data[cpu_id].append({'pid': curr_pid, 'start': start_t, 'end': current_time})
        return dict(data)

    def closeEvent(self, event):
        SCHEDULER_MANAGER.stop_schedulers()
        event.accept()