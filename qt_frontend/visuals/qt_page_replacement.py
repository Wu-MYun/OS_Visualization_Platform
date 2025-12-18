# qt_frontend/visuals/qt_page_replacement.py
# 功能：页面置换算法可视化组件

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QGroupBox, QTextEdit, QGridLayout, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import Qt, QRectF
from typing import List, Dict
import random

from src.modules_extension.extension_memory import initialize_page_table, access_page, get_page_table_status, get_page_access_history
from src.system_status import STATUS
from config import PAGE_SIZE

class QtPageReplacement(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #f8f8f8;")
        
        # 初始化页表
        self.total_frames = 4  # 物理页框数
        self.current_algorithm = "LRU"
        self.page_access_sequence = []  # 页面访问序列
        self.page_fault_count = 0  # 缺页次数
        self.page_hit_count = 0  # 命中次数
        
        initialize_page_table(self.total_frames)
        
        # 设置布局
        main_layout = QVBoxLayout(self)
        
        # 控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 可视化区域
        visualization_layout = QHBoxLayout()
        
        # 页表可视化
        page_table_group = QGroupBox("页表与物理页框")
        page_table_layout = QVBoxLayout(page_table_group)
        self.page_table_visualization = PageTableVisualizationWidget(total_frames=self.total_frames)
        page_table_layout.addWidget(self.page_table_visualization)
        visualization_layout.addWidget(page_table_group)
        
        # 页面访问历史可视化
        history_group = QGroupBox("页面访问历史")
        history_layout = QVBoxLayout(history_group)
        
        # 设置历史框的最大宽度，保持与原来一样
        history_group.setMaximumWidth(380)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # 创建页面访问历史组件
        self.history_visualization = PageAccessHistoryWidget()
        scroll_area.setWidget(self.history_visualization)
        
        history_layout.addWidget(scroll_area)
        visualization_layout.addWidget(history_group)
        
        main_layout.addLayout(visualization_layout)
        
        # 创建统计信息和日志的水平布局
        stats_log_layout = QHBoxLayout()
        
        # 统计信息
        stats_group = QGroupBox("算法性能统计")
        stats_group.setMinimumWidth(300)  # 设置最小宽度，使其稍微宽一点但不要太宽
        stats_layout = QGridLayout(stats_group)
        
        self.total_accesses_label = QLabel("总访问次数: 0")
        self.page_faults_label = QLabel("缺页次数: 0")
        self.page_hits_label = QLabel("命中次数: 0")
        self.fault_rate_label = QLabel("缺页率: 0%")
        self.hit_rate_label = QLabel("命中率: 0%")
        
        stats_layout.addWidget(self.total_accesses_label, 0, 0)
        stats_layout.addWidget(self.page_faults_label, 0, 1)
        stats_layout.addWidget(self.page_hits_label, 1, 0)
        stats_layout.addWidget(self.fault_rate_label, 1, 1)
        stats_layout.addWidget(self.hit_rate_label, 2, 0, 1, 2)
        
        stats_log_layout.addWidget(stats_group)
        
        # 日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)  # 调整日志区域高度以保持协调
        log_layout.addWidget(self.log_text)
        
        stats_log_layout.addWidget(log_group)
        
        # 将水平布局添加到主布局
        main_layout.addLayout(stats_log_layout)
        
        # 定时器用于更新可视化
        self.update_timer()
    
    def create_control_panel(self):
        """
        创建控制面板，包括算法选择、页框设置和页面访问控制
        """
        control_group = QGroupBox("控制面板")
        control_layout = QHBoxLayout(control_group)
        
        # 算法选择
        algorithm_label = QLabel("置换算法:")
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["LRU", "FIFO", "OPT"])
        self.algorithm_combo.currentTextChanged.connect(self.on_algorithm_changed)
        
        # 页框数设置
        frames_label = QLabel("物理页框数:")
        self.frames_spinbox = QSpinBox()
        self.frames_spinbox.setRange(2, 8)
        self.frames_spinbox.setValue(self.total_frames)
        self.frames_spinbox.valueChanged.connect(self.on_frames_changed)
        
        # 手动访问页面
        manual_label = QLabel("页面号:")
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setRange(0, 15)
        
        self.access_button = QPushButton("手动访问")
        self.access_button.clicked.connect(self.on_manual_access)
        
        # 生成随机序列
        self.random_button = QPushButton("随机访问")
        self.random_button.clicked.connect(self.on_random_access)
        
        # 重置
        self.reset_button = QPushButton("重置")
        self.reset_button.clicked.connect(self.on_reset)
        
        # 添加到布局
        control_layout.addWidget(algorithm_label)
        control_layout.addWidget(self.algorithm_combo)
        control_layout.addSpacing(20)
        control_layout.addWidget(frames_label)
        control_layout.addWidget(self.frames_spinbox)
        control_layout.addSpacing(20)
        control_layout.addWidget(manual_label)
        control_layout.addWidget(self.page_spinbox)
        control_layout.addWidget(self.access_button)
        control_layout.addSpacing(20)
        control_layout.addWidget(self.random_button)
        control_layout.addSpacing(20)
        control_layout.addWidget(self.reset_button)
        
        return control_group
    
    def on_algorithm_changed(self, text):
        """
        当选择的页面置换算法改变时触发
        """
        self.current_algorithm = text
        self.log_text.append(f"切换到{text}页面置换算法")
        self.on_reset()
    
    def on_frames_changed(self, value):
        """
        当物理页框数改变时触发
        """
        self.total_frames = value
        self.on_reset()
        self.log_text.append(f"设置物理页框数为{value}")
    
    def on_manual_access(self):
        """
        手动访问指定页面
        """
        page_number = self.page_spinbox.value()
        self.access_page(page_number)
    
    def on_random_access(self):
        """
        随机访问页面
        """
        page_number = random.randint(0, 15)
        self.access_page(page_number)
    
    def on_reset(self):
        """
        重置页面置换模拟
        """
        self.page_access_sequence = []
        self.page_fault_count = 0
        self.page_hit_count = 0
        initialize_page_table(self.total_frames)
        self.page_table_visualization.update_total_frames(self.total_frames)
        self.log_text.append(f"重置页面置换模拟，使用{self.total_frames}个物理页框，{self.current_algorithm}算法")
    
    def access_page(self, page_number):
        """
        访问指定页面
        """
        try:
            # 访问页面
            page_fault, replaced_page = access_page(page_number, self.current_algorithm)
            
            # 更新统计信息
            self.page_access_sequence.append(page_number)
            if page_fault:
                self.page_fault_count += 1
                if replaced_page is not None:
                    self.log_text.append(f"访问页面 {page_number}: 缺页中断！替换页面 {replaced_page}")
                else:
                    self.log_text.append(f"访问页面 {page_number}: 缺页中断！")
            else:
                self.page_hit_count += 1
                self.log_text.append(f"访问页面 {page_number}: 命中！")
                
            # 更新可视化
            self.refresh_visualization()
            
        except Exception as e:
            self.log_text.append(f"访问页面时发生错误: {str(e)}")
    
    def update_stats(self):
        """
        更新算法性能统计信息
        """
        total_accesses = len(self.page_access_sequence)
        if total_accesses > 0:
            fault_rate = (self.page_fault_count / total_accesses) * 100
            hit_rate = (self.page_hit_count / total_accesses) * 100
        else:
            fault_rate = 0
            hit_rate = 0
        
        self.total_accesses_label.setText(f"总访问次数: {total_accesses}")
        self.page_faults_label.setText(f"缺页次数: {self.page_fault_count}")
        self.page_hits_label.setText(f"命中次数: {self.page_hit_count}")
        self.fault_rate_label.setText(f"缺页率: {fault_rate:.2f}%")
        self.hit_rate_label.setText(f"命中率: {hit_rate:.2f}%")
    
    def update_timer(self):
        """
        更新定时器，用于定期刷新可视化界面
        """
        from PyQt6.QtCore import QTimer
        
        self.timer = QTimer(self)
        self.timer.setInterval(500)  # 500ms刷新一次
        self.timer.timeout.connect(self.refresh_visualization)
        self.timer.start()
    
    def refresh_visualization(self):
        """
        刷新可视化界面
        """
        with STATUS._lock:
            # 获取页表和物理页框状态
            page_table, physical_frames = get_page_table_status()
            
            # 更新页表可视化
            self.page_table_visualization.update_page_table(page_table, physical_frames)
            
            # 更新页面访问历史
            self.history_visualization.update_access_history(self.page_access_sequence)
            
            # 更新统计信息
            self.update_stats()


class PageTableVisualizationWidget(QWidget):
    def __init__(self, parent=None, total_frames: int = 4):
        super().__init__(parent)
        self.total_frames = total_frames
        self.page_table = {}  # 页表: {page_number: (frame_number, is_valid, last_accessed)}
        self.physical_frames = []  # 物理页框: [(page_number, is_occupied)]
        
        # 设置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 设置样式
        self.setMinimumSize(650, 400)  # 增加最小宽度以容纳更多页框
        self.setStyleSheet("background-color: #ffffff; border: 1px solid #ccc;")
        
        # 创建物理页框显示区域
        self.frames_widget = QWidget()
        self.frames_widget.setMinimumHeight(80)
        main_layout.addWidget(self.frames_widget)
        
        # 创建页表滚动区域
        self.page_table_scroll = QScrollArea()
        self.page_table_scroll.setMinimumHeight(150)
        self.page_table_scroll.setMaximumHeight(200)
        self.page_table_scroll.setWidgetResizable(True)
        
        # 创建页表组件
        self.page_table_widget = QTableWidget()
        self.page_table_widget.setColumnCount(3)
        self.page_table_widget.setHorizontalHeaderLabels(["页面号", "页框号", "有效位"])
        self.page_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.page_table_widget.verticalHeader().setVisible(False)
        
        # 设置页表样式
        self.page_table_widget.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #ddd;
                gridline-color: #ddd;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                padding: 5px;
                font-weight: bold;
            }
        """)
        
        # 将页表添加到滚动区域
        self.page_table_scroll.setWidget(self.page_table_widget)
        main_layout.addWidget(self.page_table_scroll)
        
        # 重定向frames_widget的paintEvent
        self.frames_widget.paintEvent = self.frames_widget_paintEvent
        
        # 初始化物理页框
        self.physical_frames = [(None, False)] * total_frames
    
    def update_page_table(self, page_table: Dict, physical_frames: List):
        """更新页表和物理页框数据"""
        self.page_table = page_table
        self.physical_frames = physical_frames
        self.update_frames_display()
        self.update_table_display()
    
    def update_total_frames(self, total_frames: int):
        """更新物理页框数量"""
        self.total_frames = total_frames
        self.physical_frames = [(None, False)] * total_frames
        self.update()
    
    def update_frames_display(self):
        """更新物理页框显示"""
        # 触发paintEvent重绘
        self.frames_widget.update()
    
    def update_table_display(self):
        """更新页表显示"""
        # 清空当前页表内容
        self.page_table_widget.setRowCount(0)
        
        # 添加页表数据
        sorted_pages = sorted(self.page_table.keys())
        for page in sorted_pages:
            frame, valid, _ = self.page_table[page]
            
            # 创建行
            row = self.page_table_widget.rowCount()
            self.page_table_widget.insertRow(row)
            
            # 设置页面号
            page_item = QTableWidgetItem(f"{page}")
            page_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.page_table_widget.setItem(row, 0, page_item)
            
            # 设置页框号
            frame_item = QTableWidgetItem(f"{frame}" if valid else "-")
            frame_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.page_table_widget.setItem(row, 1, frame_item)
            
            # 设置有效位
            valid_item = QTableWidgetItem("有效" if valid else "无效")
            valid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 更换更美观的颜色
            valid_item.setBackground(QColor(76, 175, 80) if valid else QColor(244, 67, 54))  # 改为Material Design的绿色和红色
            valid_item.setForeground(QColor(255, 255, 255))
            self.page_table_widget.setItem(row, 2, valid_item)
    
    def paintEvent(self, event):
        # 主部件不需要绘制，由子部件处理
        pass
    
    def frames_widget_paintEvent(self, event):
        """绘制物理页框"""
        painter = QPainter(self.frames_widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 设置字体
        font = QFont("Arial", 9)
        painter.setFont(font)
        
        # 绘制标题
        painter.setPen(QColor(50, 50, 50))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(10, 20, "物理页框 (Frame)")
        
        # 绘制物理页框 - 优化布局和颜色
        frame_width = 90  # 进一步增大页框尺寸
        frame_height = 75  # 进一步增大页框尺寸
        frame_spacing = 8
        
        # 计算物理页框的起始位置
        total_frames_width = (frame_width + frame_spacing) * self.total_frames - frame_spacing
        frames_start_x = max(10, (self.frames_widget.width() - total_frames_width) // 2)
        frames_start_y = 40
        
        # 绘制物理页框
        for i in range(self.total_frames):
            x = frames_start_x + i * (frame_width + frame_spacing)
            y = frames_start_y
            
            # 绘制页框边框
            painter.setPen(QPen(QColor(150, 150, 150), 2))
            
            # 根据是否被占用选择颜色 - 使用更友好的颜色
            frame = self.physical_frames[i]
            if frame[1]:  # 被占用
                painter.setBrush(QColor(70, 130, 180))  # 钢蓝色，更专业易读
            else:  # 空闲
                painter.setBrush(QColor(220, 220, 220))  # 浅灰色
            
            # 绘制页框
            painter.drawRect(x, y, frame_width, frame_height)
            
            # 绘制页框号
            painter.setPen(QColor(255, 255, 255) if frame[1] else QColor(0, 0, 0))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(x + 5, y + 15, f"Frame {i}")
            
            # 绘制页面号
            if frame[1]:  # 被占用
                painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                painter.drawText(x + 22, y + 35, f"Page {frame[0]}")  # 添加Page标签使其更清晰
            else:
                painter.setFont(QFont("Arial", 8))
                painter.setPen(QColor(100, 100, 100))
                painter.drawText(x + 15, y + 35, "空闲")


class PageAccessHistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_access_sequence = []  # 页面访问序列
        self.setMinimumSize(350, 400)  # 增加最小高度以更好地支持滚动
        self.setStyleSheet("background-color: #ffffff; border: 1px solid #ccc;")
    
    def update_access_history(self, access_sequence: List):
        """更新页面访问序列"""
        self.page_access_sequence = access_sequence
        # 重新计算并设置widget的高度以支持滚动
        if access_sequence:
            item_height = 40
            spacing = 10
            max_items_per_row = (self.width() - 40) // (40 + spacing)
            rows = len(access_sequence) // max_items_per_row
            if len(access_sequence) % max_items_per_row > 0:
                rows += 1
            # 设置widget的高度以容纳所有内容
            self.setMinimumHeight(max(400, 80 + rows * (item_height + spacing)))
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 设置字体
        font = QFont("Arial", 9)
        painter.setFont(font)
        
        # 绘制访问序列
        if not self.page_access_sequence:
            return
        
        # 计算每个页面号的位置
        item_width = 40
        item_height = 40
        spacing = 10
        max_items_per_row = (self.width() - 40) // (item_width + spacing)
        
        for i, page_number in enumerate(self.page_access_sequence):
            row = i // max_items_per_row
            col = i % max_items_per_row
            
            x = 20 + col * (item_width + spacing)
            y = 20 + row * (item_height + spacing)
            
            # 绘制页面号
            painter.setBrush(QColor(173, 216, 230))  # 浅蓝色
            painter.setPen(QPen(QColor(100, 149, 237), 2))
            painter.drawEllipse(x, y, item_width, item_height)
            
            # 绘制页面号数字
            painter.setPen(QColor(0, 0, 0))
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            painter.drawText(x + 15, y + 27, f"{page_number}")
            
            # 绘制访问顺序
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont("Arial", 7))
            painter.drawText(x + 5, y - 5, f"{i+1}")