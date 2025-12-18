# qt_frontend/visuals/qt_gantt_chart.py
# 功能：美观的 CPU 调度甘特图

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QLinearGradient
from PyQt6.QtCore import Qt, QRectF
from typing import List, Dict

class QtGanttChart(QWidget):
    def __init__(self, parent=None, num_cpus: int = 4):
        super().__init__(parent)
        self.num_cpus = num_cpus
        self.schedule_data: Dict[int, List[Dict]] = {}
        self.setMinimumHeight(300)
        # 白色背景，轻微圆角
        self.setStyleSheet("background-color: #FFFFFF; border-radius: 8px;")
        
        # 预定义一组漂亮的莫兰迪色系/扁平化颜色，用于区分进程
        self.colors = [
            QColor("#FF6B6B"), QColor("#4ECDC4"), QColor("#45B7D1"), 
            QColor("#FFA07A"), QColor("#98D8C8"), QColor("#F7DC6F"),
            QColor("#BB8FCE"), QColor("#F1948A"), QColor("#85C1E9")
        ]
        self.pid_color_map = {}
    
    def _draw_legend(self, painter, margin_left, margin_right, margin_top, margin_bottom, w, h):
        """绘制图例"""
        legend_x = w - margin_right + 20
        legend_y = margin_top
        
        # 只显示当前存在的进程
        current_pids = set()
        for events in self.schedule_data.values():
            for event in events:
                current_pids.add(event['pid'])
        
        # 绘制图例标题
        painter.setPen(QColor("#333333"))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(legend_x, legend_y + 15, "图例 (Process Legend)")
        
        # 绘制每个进程的图例项
        for i, pid in enumerate(current_pids):
            y = legend_y + 30 + i * 25
            
            # 绘制颜色方块
            color = self._get_color(pid)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            rect = QRectF(legend_x, y, 15, 15)
            painter.drawRoundedRect(rect, 3, 3)
            
            # 绘制 PID 标签
            painter.setPen(QColor("#555555"))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(legend_x + 25, y + 12, f"P{pid}")

    def update_schedule_data(self, schedule_data: Dict[int, List[Dict]]):
        self.schedule_data = schedule_data
        self.update()

    def _get_color(self, pid):
        if pid not in self.pid_color_map:
            self.pid_color_map[pid] = self.colors[pid % len(self.colors)]
        return self.pid_color_map[pid]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        
        # 布局参数
        margin_left = 80
        margin_right = 150  # 增加右边距用于放置图例
        margin_top = 40
        margin_bottom = 40
        
        # 1. 绘制标题背景栏
        header_rect = QRectF(0, 0, w, 30)
        painter.fillRect(header_rect, QColor("#F5F5F5"))
        painter.setPen(QColor("#333333"))
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, "CPU 核心调度时序图 (Gantt Chart)")

        # 计算绘图区
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom
        row_h = chart_h / self.num_cpus
        bar_h = row_h * 0.6  # 进度条高度占行高的 60%

        # 2. 计算时间比例
        max_time = 0
        for events in self.schedule_data.values():
            if events:
                max_time = max(max_time, events[-1]['end'])
        
        # 至少显示 10 秒刻度
        max_time = max(max_time, 10.0)
        time_scale = chart_w / max_time

        # 3. 绘制每个 CPU 轨道
        for i in range(self.num_cpus):
            y_base = margin_top + i * row_h
            y_center = y_base + row_h / 2
            
            # 绘制轨道背景线
            painter.setPen(QPen(QColor("#E0E0E0"), 1))
            painter.drawLine(int(margin_left), int(y_center), int(w - margin_right), int(y_center))
            
            # 绘制左侧 CPU 标签
            painter.setPen(QColor("#555555"))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            label_rect = QRectF(0, y_base, margin_left - 10, row_h)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"CPU-{i}")

            # 绘制任务块
            tasks = self.schedule_data.get(i, [])
            for task in tasks:
                pid = task['pid']
                start = task['start']
                end = task['end']
                
                x = margin_left + start * time_scale
                width = (end - start) * time_scale
                
                # 忽略太短的绘制
                if width < 1: continue

                rect = QRectF(x, y_center - bar_h/2, width, bar_h)
                
                # 渐变填充
                base_color = self._get_color(pid)
                gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                gradient.setColorAt(0, base_color.lighter(110))
                gradient.setColorAt(1, base_color)
                
                painter.setBrush(gradient)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 4, 4)
                
                # 绘制 PID 文字
                if width > 20: # 空间够才写字
                    painter.setPen(QColor("white"))
                    painter.setFont(QFont("Arial", 8))
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"P{pid}")

        # 4. 绘制底部时间轴
        painter.setPen(QPen(QColor("#888888"), 1))
        axis_y = h - margin_bottom + 10
        painter.drawLine(int(margin_left), int(axis_y), int(w - margin_right), int(axis_y))
        
        # 动态计算刻度间隔 (1s, 2s, 5s, 10s...)
        step = 1
        if max_time > 20: step = 2
        if max_time > 50: step = 5
        if max_time > 100: step = 10
        
        painter.setFont(QFont("Arial", 8))
        for t in range(0, int(max_time) + 2, step):
            x = margin_left + t * time_scale
            if x > w - margin_right: break
            
            painter.drawLine(int(x), int(axis_y), int(x), int(axis_y + 5))
            painter.drawText(int(x - 15), int(axis_y + 20), f"{t}s")
        
        # 5. 绘制图例
        self._draw_legend(painter, margin_left, margin_right, margin_top, margin_bottom, w, h)