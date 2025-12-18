# qt_frontend/visuals/qt_process_states.py
# 功能：新页面 - 进程状态转换图与实时数据看板

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QListWidget, QListWidgetItem, QGroupBox, QSplitter)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF
import math
from src.process_model import ProcessState

class QtProcessStateDiagram(QWidget):
    """左侧：绘制状态转换图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(500)
        self.setStyleSheet("background-color: white;")
        self.processes = []
        
        # 优化布局坐标定义，使整体更加平衡
        cx, cy = 350, 280 # 中心点
        self.nodes = {
            ProcessState.NEW:        QPointF(120, 280),   # 左移一点
            ProcessState.READY:      QPointF(350, 120),   # 上移一点
            ProcessState.RUNNING:    QPointF(580, 280),   # 右移一点
            ProcessState.BLOCKED:    QPointF(350, 440),   # 下移一点
            ProcessState.TERMINATED: QPointF(810, 280)    # 右移更多，增加与RUNNING的距离
        }
        
        self.node_colors = {
            ProcessState.NEW:        QColor("#A9DFBF"), # 浅绿
            ProcessState.READY:      QColor("#F9E79F"), # 浅黄
            ProcessState.RUNNING:    QColor("#F5B7B1"), # 浅红
            ProcessState.BLOCKED:    QColor("#D7BDE2"), # 浅紫
            ProcessState.TERMINATED: QColor("#CCD1D1")  # 灰色
        }
        
        self.radius = 50 # 增加节点半径，使文字更易显示

    def update_data(self, processes):
        self.processes = processes
        self.update() # 触发重绘

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. 绘制连线 (箭头)
        self._draw_arrow(painter, ProcessState.NEW, ProcessState.READY)
        self._draw_arrow(painter, ProcessState.READY, ProcessState.RUNNING)
        self._draw_arrow(painter, ProcessState.RUNNING, ProcessState.READY, offset=20) # 抢占
        self._draw_arrow(painter, ProcessState.RUNNING, ProcessState.BLOCKED)
        self._draw_arrow(painter, ProcessState.BLOCKED, ProcessState.READY)
        self._draw_arrow(painter, ProcessState.RUNNING, ProcessState.TERMINATED)

        # 2. 绘制状态大圆
        for state, pos in self.nodes.items():
            # 阴影
            painter.setBrush(QColor(0,0,0,20))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(pos + QPointF(3,3), self.radius, self.radius)
            
            # 本体
            painter.setBrush(self.node_colors[state])
            painter.setPen(QPen(QColor("#555"), 2))
            painter.drawEllipse(pos, self.radius, self.radius)
            
            # 文字
            painter.setPen(QColor("black"))
            painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            text_rect = QRectF(pos.x()-self.radius, pos.y()-self.radius, self.radius*2, self.radius*2)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, state.value)

        # 3. 绘制进程小点
        self._draw_process_dots(painter)

    def _draw_arrow(self, painter, start_state, end_state, offset=0):
        start = self.nodes[start_state]
        end = self.nodes[end_state]
        
        # 简单计算连线方向
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.hypot(dx, dy)
        
        # 归一化方向向量
        if length == 0: return
        nx, ny = dx/length, dy/length
        
        # 计算圆周上的点
        start_p = QPointF(start.x() + nx*self.radius, start.y() + ny*self.radius)
        end_p = QPointF(end.x() - nx*self.radius, end.y() - ny*self.radius)
        
        # 偏移 (用于双向箭头不重叠)
        if offset != 0:
            perp_x, perp_y = -ny, nx
            start_p += QPointF(perp_x*offset, perp_y*offset)
            end_p += QPointF(perp_x*offset, perp_y*offset)

        painter.setPen(QPen(QColor("#666"), 2))
        painter.drawLine(start_p, end_p)
        
        # 画箭头头
        arrow_size = 10
        angle = math.atan2(dy, dx)
        p1 = end_p - QPointF(math.cos(angle - math.pi/6)*arrow_size, math.sin(angle - math.pi/6)*arrow_size)
        p2 = end_p - QPointF(math.cos(angle + math.pi/6)*arrow_size, math.sin(angle + math.pi/6)*arrow_size)
        
        arrow_head = QPolygonF([end_p, p1, p2])
        painter.setBrush(QColor("#666"))
        painter.drawPolygon(arrow_head)

    def _draw_process_dots(self, painter):
        """在状态节点周围绘制代表进程的小圆点，优化显示避免重叠"""
        # 按状态分组
        grouped = {s: [] for s in ProcessState}
        for p in self.processes:
            grouped[p.state].append(p)
            
        dot_radius = 7
        orbit_radius = self.radius + 12
        
        for state, procs in grouped.items():
            center = self.nodes[state]
            count = len(procs)
            if count == 0: continue
            
            # 优化角度分布，避免拥挤
            if count <= 8:
                angle_step = 360 / count
            elif count <= 16:
                angle_step = 360 / (count / 2)
                orbit_radius_outer = orbit_radius + 2 * dot_radius + 4
            else:
                angle_step = 360 / (count / 3)
                orbit_radius_outer = orbit_radius + 2 * dot_radius + 4
                orbit_radius_outer2 = orbit_radius_outer + 2 * dot_radius + 4
            
            for i, p in enumerate(procs):
                angle_deg = (i % (count if count <= 8 else (count//2 if count <=16 else count//3))) * angle_step
                angle_rad = math.radians(angle_deg)
                
                # 根据进程数量选择不同的轨道半径
                if count <= 8:
                    current_orbit_radius = orbit_radius
                elif i < count//2:
                    current_orbit_radius = orbit_radius
                elif i < count and count <=16:
                    current_orbit_radius = orbit_radius_outer
                elif i < count//3:
                    current_orbit_radius = orbit_radius
                elif i < 2*count//3:
                    current_orbit_radius = orbit_radius_outer
                else:
                    current_orbit_radius = orbit_radius_outer2
                
                x = center.x() + current_orbit_radius * math.cos(angle_rad)
                y = center.y() + current_orbit_radius * math.sin(angle_rad)
                
                # 绘制小点 - 深色背景确保白色文字清晰可见
                painter.setBrush(QColor("#2980B9"))  # 更深的蓝色背景
                painter.setPen(QColor("white"))
                painter.drawEllipse(QPointF(x, y), dot_radius, dot_radius)
                
                # PID - 确保数字清晰可见
                painter.setPen(QColor("white"))
                painter.setFont(QFont("Arial", 7, QFont.Weight.Bold))
                pid_text = str(p.pid)
                text_rect = QRectF(x-dot_radius, y-dot_radius, dot_radius*2, dot_radius*2)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, pid_text)


class QtProcessStates(QWidget):
    """主控件：包含左侧绘图和右侧数据列表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #F5F5F5;")
        layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：图
        self.diagram = QtProcessStateDiagram()
        splitter.addWidget(self.diagram)
        
        # 右侧：实时数据列表
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: white; border-radius: 8px; margin: 5px;")
        right_layout = QVBoxLayout(right_widget)
        
        # 添加标题标签，设置合适的字体和颜色
        title_label = QLabel("进程实时状态数据:")
        title_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #2E86C1; margin: 10px;")
        right_layout.addWidget(title_label)
        
        # 设置列表控件的样式和属性
        self.info_list = QListWidget()
        self.info_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                font-family: Arial, sans-serif;
                font-size: 10pt;
                padding: 5px;
                background-color: #FAFAFA;
            }
            QListWidget::item {
                padding: 10px;
                margin: 2px 0;
                border-radius: 3px;
            }
            QListWidget::item:hover {
                background-color: #E3F2FD;
            }
        """)
        # 启用水平滚动条，确保信息显示完整
        self.info_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_layout.addWidget(self.info_list)
        
        splitter.addWidget(right_widget)
        # 增加右侧信息列表的空间占比
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)

    def update_processes(self, processes):
        # 更新左侧图
        self.diagram.update_data(processes)
        
        # 更新右侧列表
        self.info_list.clear()
        # 按 PID 排序
        sorted_procs = sorted(processes, key=lambda x: x.pid)
        
        for p in sorted_procs:
            # 改进文本格式，确保信息完整显示
            state_text = p.state.value  # 显示完整状态名称
            item_text = f"PID: {p.pid} | 状态: {state_text} | 剩余: {p.remaining_time:.1f}s"
            if p.state == ProcessState.RUNNING:
                # 检查对象是否有cpu_id属性（避免RTOS_Task对象出现AttributeError）
                if hasattr(p, 'cpu_id'):
                    item_text += f" [CPU-{p.cpu_id}]"
            elif p.state == ProcessState.BLOCKED:
                item_text += " [IO]"
                
            item = QListWidgetItem(item_text)
            
            # 设置背景和文字颜色
            if p.state == ProcessState.RUNNING:
                item.setForeground(QColor("black"))  # 黑色字体
                item.setBackground(QColor("#E74C3C"))  # 红色背景
            elif p.state == ProcessState.READY:
                item.setForeground(QColor("black"))  # 黑色字体
                item.setBackground(QColor("#F9E79F"))  # 黄色背景
            elif p.state == ProcessState.BLOCKED:
                item.setForeground(QColor("black"))  # 黑色字体
                item.setBackground(QColor("#8E44AD"))  # 紫色背景
            elif p.state == ProcessState.TERMINATED:
                item.setForeground(QColor("black"))  # 黑色字体
                item.setBackground(QColor("#ECF0F1"))  # 灰色背景
            else:
                item.setForeground(QColor("black"))  # 黑色字体
                item.setBackground(QColor("#A9DFBF"))  # 绿色背景
                
            self.info_list.addItem(item)