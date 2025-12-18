# qt_frontend/visuals/qt_memory_allocation.py
# 功能：动态内存分配可视化组件

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QGroupBox, QTextEdit
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import Qt, QRectF
from typing import List, Dict

from src.modules_extension.extension_memory import initialize_memory, first_fit_allocate, best_fit_allocate, worst_fit_allocate, deallocate_memory
from src.system_status import STATUS
from config import MEMORY_SIZE

class QtMemoryAllocation(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #f8f8f8;")
        
        # 初始化内存
        initialize_memory()
        
        # 当前选中的内存分配算法
        self.current_algorithm = "First Fit"
        
        # 设置布局
        main_layout = QVBoxLayout(self)
        
        # 控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 内存可视化区域
        memory_group = QGroupBox("内存分配可视化")
        memory_layout = QVBoxLayout(memory_group)
        self.memory_visualization = MemoryVisualizationWidget(total_memory=MEMORY_SIZE)
        memory_layout.addWidget(self.memory_visualization)
        main_layout.addWidget(memory_group)
        
        # 内存统计信息
        stats_group = QGroupBox("内存统计信息")
        stats_layout = QHBoxLayout(stats_group)
        
        self.total_memory_label = QLabel(f"总内存: {MEMORY_SIZE} MB")
        self.used_memory_label = QLabel("已用内存: 0 MB")
        self.free_memory_label = QLabel("空闲内存: 0 MB")
        self.free_blocks_label = QLabel("空闲块数: 0")
        self.allocated_blocks_label = QLabel("已分配块数: 0")
        
        stats_layout.addWidget(self.total_memory_label)
        stats_layout.addWidget(self.used_memory_label)
        stats_layout.addWidget(self.free_memory_label)
        stats_layout.addWidget(self.free_blocks_label)
        stats_layout.addWidget(self.allocated_blocks_label)
        
        main_layout.addWidget(stats_group)
        
        # 日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # 增加日志区域最大高度以扩大显示空间s
        self.log_text.setMaximumHeight(280)
        # 设置样式表消除文字上下空白
        self.log_text.setStyleSheet("""
            QTextEdit {
                padding: 0px;
                margin: 0px;
                font-family: Consolas;
                font-size: 9pt;
                line-height: 1.0;
                border: 1px solid #C2C7CB;
            }
        """)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)
        
        # 定时器用于更新可视化
        self.update_timer()
    
    def create_control_panel(self):
        """
        创建控制面板，包括算法选择、内存分配和回收按钮
        """
        control_group = QGroupBox("控制面板")
        control_layout = QHBoxLayout(control_group)
        
        # 算法选择
        algorithm_label = QLabel("分配算法:")
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["First Fit", "Best Fit", "Worst Fit"])
        self.algorithm_combo.currentTextChanged.connect(self.on_algorithm_changed)
        
        # 内存分配
        allocate_label = QLabel("分配大小 (MB):")
        self.allocate_size_combo = QComboBox()
        self.allocate_size_combo.addItems(["64", "128", "256", "512"])
        
        self.allocate_button = QPushButton("分配内存")
        self.allocate_button.clicked.connect(self.on_allocate_memory)
        
        # 内存回收
        deallocate_label = QLabel("选择进程:")
        self.deallocate_combo = QComboBox()
        
        self.deallocate_button = QPushButton("回收内存")
        self.deallocate_button.clicked.connect(self.on_deallocate_memory)
        
        # 重置内存按钮
        self.reset_button = QPushButton("重置内存")
        self.reset_button.clicked.connect(self.on_reset_memory)
        
        # 添加到布局
        control_layout.addWidget(algorithm_label)
        control_layout.addWidget(self.algorithm_combo)
        control_layout.addSpacing(20)
        control_layout.addWidget(allocate_label)
        control_layout.addWidget(self.allocate_size_combo)
        control_layout.addWidget(self.allocate_button)
        control_layout.addSpacing(20)
        control_layout.addWidget(deallocate_label)
        control_layout.addWidget(self.deallocate_combo)
        control_layout.addWidget(self.deallocate_button)
        control_layout.addSpacing(20)
        control_layout.addWidget(self.reset_button)
        
        return control_group
    
    def on_algorithm_changed(self, text):
        """
        当选择的内存分配算法改变时触发
        """
        self.current_algorithm = text
        self.log_text.append(f"切换到{text}分配算法")
    
    def on_allocate_memory(self):
        """
        当点击分配内存按钮时触发
        """
        try:
            size = int(self.allocate_size_combo.currentText())
            
            # 生成一个新的进程ID（简单实现）
            with STATUS._lock:
                # 找到最大的PID
                max_pid = max([block[3] for block in STATUS.memory_layout if block[3] != -1], default=0)
                new_pid = max_pid + 1
            
            # 根据选择的算法分配内存
            if self.current_algorithm == "First Fit":
                success = first_fit_allocate(new_pid, size)
            elif self.current_algorithm == "Best Fit":
                success = best_fit_allocate(new_pid, size)
            elif self.current_algorithm == "Worst Fit":
                success = worst_fit_allocate(new_pid, size)
            
            if success:
                self.log_text.append(f"使用{self.current_algorithm}成功分配{size}MB内存给PID{new_pid}")
                # 更新进程选择下拉框
                self.update_deallocate_combo()
            else:
                self.log_text.append(f"使用{self.current_algorithm}分配{size}MB内存失败")
                
        except Exception as e:
            self.log_text.append(f"分配内存时发生错误: {str(e)}")
    
    def on_deallocate_memory(self):
        """
        当点击回收内存按钮时触发
        """
        try:
            if self.deallocate_combo.currentIndex() == -1:
                self.log_text.append("请选择要回收内存的进程")
                return
            
            pid = int(self.deallocate_combo.currentText().split()[1])
            deallocate_memory(pid)
            self.log_text.append(f"成功回收PID{pid}的内存")
            
            # 更新进程选择下拉框
            self.update_deallocate_combo()
            
        except Exception as e:
            self.log_text.append(f"回收内存时发生错误: {str(e)}")
    
    def on_reset_memory(self):
        """
        当点击重置按钮时触发，回收所有内存
        """
        try:
            from src.modules_extension.extension_memory import reset_memory
            reset_memory()
            self.log_text.append("成功重置所有内存")
            
            # 更新进程选择下拉框
            self.update_deallocate_combo()
            
        except Exception as e:
            self.log_text.append(f"重置内存时发生错误: {str(e)}")
    
    def update_deallocate_combo(self):
        """
        更新回收内存时的进程选择下拉框
        """
        with STATUS._lock:
            # 获取所有已分配的进程ID
            allocated_pids = set()
            for block in STATUS.memory_layout:
                if block[2] and block[3] != -1:
                    allocated_pids.add(block[3])
            
            # 更新下拉框
            self.deallocate_combo.clear()
            for pid in sorted(allocated_pids):
                self.deallocate_combo.addItem(f"PID {pid}")
    
    def update_memory_stats(self):
        """
        更新内存统计信息
        """
        with STATUS._lock:
            used_memory = 0
            free_memory = 0
            free_blocks = 0
            allocated_blocks = 0
            
            for block in STATUS.memory_layout:
                if block[2]:  # 已分配
                    used_memory += block[1]
                    allocated_blocks += 1
                else:  # 空闲
                    free_memory += block[1]
                    free_blocks += 1
            
            self.used_memory_label.setText(f"已用内存: {used_memory} MB")
            self.free_memory_label.setText(f"空闲内存: {free_memory} MB")
            self.free_blocks_label.setText(f"空闲块数: {free_blocks}")
            self.allocated_blocks_label.setText(f"已分配块数: {allocated_blocks}")
    
    def update_timer(self):
        """
        更新定时器，用于定期刷新可视化界面
        """
        from PyQt6.QtCore import QTimer
        
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # 1秒刷新一次
        self.timer.timeout.connect(self.refresh_visualization)
        self.timer.start()
    
    def refresh_visualization(self):
        """
        刷新可视化界面
        """
        with STATUS._lock:
            # 更新内存可视化
            self.memory_visualization.update_memory(STATUS.memory_layout)
            
            # 更新内存统计信息
            self.update_memory_stats()


class MemoryVisualizationWidget(QWidget):
    def __init__(self, parent=None, total_memory: int = 1024):
        super().__init__(parent)
        self.total_memory = total_memory  # 总内存（MB）
        self.memory_blocks = []  # 内存块：[(start, size, is_allocated, pid)]
        self.setMinimumSize(600, 200)
        self.setStyleSheet("background-color: #ffffff; border: 1px solid #ccc;")
    
    def update_memory(self, blocks: List):
        """更新内存块数据"""
        self.memory_blocks = blocks
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 设置字体
        font = QFont("Arial", 9)
        painter.setFont(font)
        
        # 绘制内存分区条
        bar_height = 100
        bar_y = 50
        scale = (self.width() - 40) / self.total_memory  # 缩放比例
        
        # 绘制内存条背景
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setBrush(QColor(240, 240, 240))
        painter.drawRect(20, bar_y, self.width() - 40, bar_height)
        
        # 绘制每个内存块
        for block in self.memory_blocks:
            start_x = 20 + block[0] * scale
            width = block[1] * scale
            
            # 根据是否已分配选择颜色
            if block[2]:  # 已分配
                # 为不同的PID分配不同的颜色
                pid_color = self.get_color_for_pid(block[3])
                painter.setBrush(pid_color)
            else:  # 空闲
                painter.setBrush(QColor(220, 220, 220))
            
            # 绘制内存块
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawRect(int(start_x), bar_y, int(width), bar_height)
            
            # 绘制内存块信息
            if width > 30:  # 足够宽才显示文字
                # 使用小字体
                font = QFont("Arial", 7)
                painter.setFont(font)
                
                text = f"{block[0]}-{block[0]+block[1]}MB"
                if block[2]:
                    text += f" (PID{block[3]})"
                
                painter.setPen(QColor(0, 0, 0))
                # 计算文本区域并居中显示
                text_rect = painter.boundingRect(int(start_x + 5), bar_y + 10, int(width - 10), bar_height - 20, Qt.AlignmentFlag.AlignCenter, text)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        
        # 绘制标题
        painter.setPen(QColor(50, 50, 50))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(20, 30, "动态内存分配可视化")
        
        # 绘制底部刻度
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor(100, 100, 100))
        
        # 刻度间隔
        interval = self.total_memory // 8
        for i in range(0, self.total_memory + 1, interval):
            x = 20 + i * scale
            painter.drawLine(int(x), bar_y + bar_height + 5, int(x), bar_y + bar_height + 10)
            painter.drawText(int(x - 10), bar_y + bar_height + 25, f"{i}MB")
    
    def get_color_for_pid(self, pid: int) -> QColor:
        """
        根据PID生成唯一的颜色
        """
        colors = [
            QColor(144, 238, 144),  # 浅绿
            QColor(255, 182, 193),  # 浅粉
            QColor(173, 216, 230),  # 浅蓝
            QColor(255, 228, 181),  # 浅橙
            QColor(221, 160, 221),  # 浅紫
            QColor(152, 251, 152),  # 薄荷绿
            QColor(255, 192, 203),  # 粉红
            QColor(135, 206, 235),  # 天蓝
            QColor(255, 235, 205),  # 小麦色
            QColor(218, 112, 214),  # 紫罗兰
        ]
        return colors[pid % len(colors)]