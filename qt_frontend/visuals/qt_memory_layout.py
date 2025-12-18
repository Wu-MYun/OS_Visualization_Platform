# visuals/qt_memory_layout.py
# 功能：绘制动态内存分区+页表可视化
from PyQt6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QRectF
from typing import List, Dict

class QtMemoryLayout(QWidget):
    def __init__(self, parent=None, total_memory: int = 1024):
        super().__init__(parent)
        self.total_memory = total_memory  # 总内存（MB）
        self.memory_blocks: List[Dict] = []  # 内存块：[{start:0, end:1024, is_used:False, pid:-1}]
        self.page_table: List[Dict] = []  # 页表：[{pid:1, page:0, frame:2}]
        self.setMinimumSize(600, 200)
        self.setStyleSheet("background-color: #f8f8f8; border: 1px solid #ccc;")

    def update_memory(self, blocks: List[Dict], page_table: List[Dict]):
        """更新内存块和页表数据"""
        self.memory_blocks = blocks
        self.page_table = page_table
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(200, 200, 200), 1)
        painter.setPen(pen)

        # 1. 绘制内存分区条
        bar_height = 50
        bar_y = 20
        scale = (self.width() - 40) / self.total_memory  # 缩放比例

        for block in self.memory_blocks:
            start_x = 20 + block["start"] * scale
            width = (block["end"] - block["start"]) * scale
            # 已分配→绿色，空闲→灰色
            color = QColor(144, 238, 144) if block["is_used"] else QColor(220, 220, 220)
            painter.setBrush(color)
            painter.drawRect(int(start_x), bar_y, int(width), bar_height)
            # 绘制内存块信息
            text = f"{block['start']}-{block['end']}MB"
            if block["is_used"]:
                text += f" (PID{block['pid']})"
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(int(start_x + 5), bar_y + 25, text)

        # 2. 绘制页表（下方）
        painter.drawText(20, bar_y + 80, "页表（PID-页号→物理块号）")
        table_x, table_y = 20, bar_y + 90
        row_height = 20
        # 绘制表头
        painter.drawText(table_x, table_y, "PID")
        painter.drawText(table_x + 50, table_y, "页号")
        painter.drawText(table_x + 100, table_y, "物理块号")
        # 绘制页表内容
        for i, entry in enumerate(self.page_table[:5]):  # 最多显示5行
            y = table_y + (i+1)*row_height
            painter.drawText(table_x, y, str(entry["pid"]))
            painter.drawText(table_x + 50, y, str(entry["page"]))
            painter.drawText(table_x + 100, y, str(entry["frame"]))