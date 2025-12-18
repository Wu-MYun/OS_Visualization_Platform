# visuals/qt_rtos_timeline.py
# 修复版 V6：使用 ID 过滤日志，解决时间戳冲突导致的日志丢失问题

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QTableWidget, QTableWidgetItem, QTextEdit, 
                             QPushButton, QGridLayout, QHeaderView, QSplitter)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import Qt, QRectF

from src.system_status import STATUS
from src.process_model import ProcessState
from src.modules_extension.extension_rtos import cpu_registers, trigger_external_interrupt, reset_rtos_data

# === 内部类 1: 逻辑分析仪绘图画布 ===
class RTOSLogicAnalyzer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(280)
        self.setStyleSheet("background-color: #1E1E1E;")
        self.timeline_data = []
        self.pixels_per_ms = 4 
        self.row_height = 40  
        self.left_margin = 120
        
        self.c_high = QColor(0, 255, 127)   
        self.c_isr = QColor(255, 50, 50)    
        self.c_grid = QColor(60, 60, 60)
        self.c_text = QColor(220, 220, 220)
        self.c_bg_row = QColor(30, 30, 30)

        self.current_running_pid = -1

    def update_data(self, data):
        self.timeline_data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1E1E1E"))
        
        current_sim_time = STATUS.global_timer

        self.current_running_pid = -1
        if self.timeline_data:
            last_evt = self.timeline_data[-1]
            if last_evt['type'] in ['TASK_SWITCH', 'ISR_EXEC']:
                self.current_running_pid = last_evt['next_pid']

        view_w = (self.width() - self.left_margin) / self.pixels_per_ms
        end_t = current_sim_time + 10  
        start_t = max(0, end_t - view_w)

        active_pids = set(STATUS.all_processes.keys())
        for evt in self.timeline_data:
            if evt['prev_pid'] != -1: active_pids.add(evt['prev_pid'])
            if evt['next_pid'] != -1: active_pids.add(evt['next_pid'])
        
        sorted_pids = []
        normal_pids = []
        isr_pids = []

        for pid in active_pids:
            task = STATUS.all_processes.get(pid)
            is_isr = False
            if task and getattr(task, 'is_isr', False): is_isr = True
            elif pid >= 90: is_isr = True
            
            if is_isr: isr_pids.append(pid)
            else: normal_pids.append(pid)
        
        sorted_pids = sorted(isr_pids) + sorted(normal_pids)

        pid_y_map = {}
        for i, pid in enumerate(sorted_pids):
            y = 40 + i * self.row_height
            pid_y_map[pid] = y
            self._draw_row_background(painter, pid, y)

        self._draw_intervals(painter, pid_y_map, start_t, current_sim_time)
        self._draw_ruler(painter, start_t, end_t)
        
        line_x = self.left_margin + (current_sim_time - start_t) * self.pixels_per_ms
        painter.setPen(QPen(QColor("#FFD700"), 2))
        painter.drawLine(int(line_x), 0, int(line_x), self.height())
        painter.setBrush(QColor("#FFD700"))
        painter.drawEllipse(int(line_x)-4, 25, 8, 8)

    def _draw_row_background(self, painter, pid, y):
        painter.fillRect(0, int(y), self.width(), int(self.row_height), self.c_bg_row)
        painter.setPen(QPen(self.c_grid, 1))
        painter.drawLine(self.left_margin, int(y + self.row_height), self.width(), int(y + self.row_height))

        task = STATUS.all_processes.get(pid)
        is_isr = (task and getattr(task, 'is_isr', False)) or (pid >= 90)
        
        if is_isr:
            txt = f"[ISR] IRQ-{pid}"
            color = self.c_isr
        else:
            prio = task.priority if task else "?"
            txt = f"Task {pid} (P{prio})"
            color = self.c_high
            
        rect = QRectF(0, y, self.left_margin, self.row_height)
        painter.setPen(self.c_text)
        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold if is_isr else QFont.Weight.Normal))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

        is_active = (pid == self.current_running_pid)
        draw_color = color if is_active else QColor(50, 50, 50)
        if is_active and is_isr: draw_color = self.c_isr 
        
        painter.setBrush(draw_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(15, int(y + 15), 10, 10)
        
        if is_active:
            painter.setOpacity(0.3)
            painter.drawEllipse(11, int(y + 11), 18, 18)
            painter.setOpacity(1.0)

    def _draw_intervals(self, painter, pid_y_map, start_t, current_time):
        if not self.timeline_data: return
        intervals = []
        last_time = 0
        last_pid = -1
        
        for ev in self.timeline_data:
            ev_time = ev['time']
            if ev_time > last_time and last_pid != -1:
                intervals.append({'pid': last_pid, 'start': last_time, 'end': ev_time})
            if ev['type'] in ["SWITCH_START", "IDLE", "BLOCKED", "TASK_FINISH"]:
                last_pid = -1
            elif ev['type'] in ["TASK_SWITCH", "ISR_EXEC"]:
                last_pid = ev['next_pid']
            last_time = ev_time

        if last_pid != -1 and current_time > last_time:
            intervals.append({'pid': last_pid, 'start': last_time, 'end': current_time})

        for seg in intervals:
            pid = seg['pid']
            if pid not in pid_y_map: continue
            y = pid_y_map[pid]
            x_start = self.left_margin + (seg['start'] - start_t) * self.pixels_per_ms
            x_end = self.left_margin + (seg['end'] - start_t) * self.pixels_per_ms
            draw_x = max(self.left_margin, x_start)
            draw_w = max(0, x_end - draw_x)
            if draw_w <= 0 or x_start > self.width(): continue

            is_isr = (pid >= 90)
            base_color = self.c_isr if is_isr else self.c_high
            
            painter.setBrush(base_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(draw_x, y + 10, draw_w, self.row_height - 20))
            if is_isr:
                painter.setBrush(QColor(255, 255, 255, 100))
                painter.drawRect(QRectF(draw_x, y + 10, draw_w, self.row_height - 20))

    def _draw_ruler(self, painter, start_t, end_t):
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QPen(self.c_text, 1))
        ruler_height = 30
        painter.drawLine(self.left_margin, ruler_height, self.width(), ruler_height)
        
        tick_interval = 20
        major_tick_time = ((int(start_t) // tick_interval) + 1) * tick_interval
        
        while major_tick_time < end_t:
            x = self.left_margin + (major_tick_time - start_t) * self.pixels_per_ms
            painter.drawLine(int(x), ruler_height - 10, int(x), ruler_height)
            painter.drawText(int(x) - 20, ruler_height - 15, f"{major_tick_time}ms")
            major_tick_time += tick_interval


# === 内部类 2: 寄存器与中文分析报告 ===
class CpuStatePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        # === 核心修改：改为使用 ID 跟踪 ===
        self.last_processed_id = -1 

        reg_group = QGroupBox("Cortex-M 寄存器状态")
        reg_layout = QGridLayout(reg_group)
        self.reg_labels = {}
        regs = ["R0", "R1", "R2", "R3", "R12", "LR", "PC", "SP"]
        for i, r in enumerate(regs):
            reg_layout.addWidget(QLabel(f"{r}:"), i//2, (i%2)*2)
            lbl = QLabel("00000000")
            lbl.setStyleSheet("font-family: Consolas; color: #00FF7F; background: #333; border: 1px solid #555; padding: 2px;")
            self.reg_labels[r] = lbl
            reg_layout.addWidget(lbl, i//2, (i%2)*2+1)
        layout.addWidget(reg_group, 1)

        report_group = QGroupBox("实时内核分析报告 (Real-time Log)")
        rep_layout = QVBoxLayout(report_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #2D2D30; color: #E0E0E0; font-family: 'Microsoft YaHei UI', Consolas; font-size: 10pt;")
        rep_layout.addWidget(self.log_text)
        layout.addWidget(report_group, 2) 

    def reset(self):
        self.log_text.clear()
        self.last_processed_id = -1 
        self.update_state()

    def update_log(self, data):
        if not data: return
        # 按 ID 排序确保顺序正确
        all_events = sorted(list(data), key=lambda x: x.get('id', -1))
        
        for evt in all_events:
            # === 核心修改：使用 ID 判断新旧 ===
            eid = evt.get('id', -1)
            if eid > self.last_processed_id:
                self._append_single_log(evt)
                self.last_processed_id = eid

    def _append_single_log(self, evt):
        t = evt['time']
        msg = ""
        color = "#FFFFFF"
        reason = evt.get('info', '')

        if evt['type'] == "ISR_TRIGGER":
            msg = f"[T={t}ms] 🚨 <b>中断触发 (IRQ)</b>: <br>&nbsp;&nbsp;检测到外部硬件中断! 系统准备响应..."
            color = "#FF0000" 
        elif evt['type'] == "ISR_EXEC":
            msg = f"[T={t}ms] ⚡ <b>执行中断服务程序 (ISR)</b>: <br>&nbsp;&nbsp;P{evt['prev_pid']} 被抢占 -> 执行 ISR-{evt['next_pid']}<br>&nbsp;&nbsp;原因: {reason}"
            color = "#FFA500" 
        elif evt['type'] == "ISR_FINISH":
            msg = f"[T={t}ms] ✅ <b>中断结束</b>: <br>&nbsp;&nbsp;ISR 执行完毕，返回线程模式。"
            color = "#32CD32" 
        elif evt['type'] == "TASK_SWITCH":
            next_task_info = ""
            if 'next_pid' in evt and evt['next_pid'] != -1 and evt['next_pid'] in STATUS.all_processes:
                task = STATUS.all_processes[evt['next_pid']]
                next_task_info = f" (优先级: {task.priority})"
            msg = f"[T={t}ms] 🔄 <b>任务切换</b>: P{evt['prev_pid']} -> P{evt['next_pid']}{next_task_info} ({reason})"
            color = "#00CED1" 
        elif evt['type'] == "BLOCKED":
            msg = f"[T={t}ms] 🛑 <b>阻塞</b>: P{evt['prev_pid']} 等待资源"
            color = "#808080" 
        elif evt['type'] == "WAKEUP":
            msg = f"[T={t}ms] 🔔 <b>唤醒</b>: P{evt['next_pid']} 进入就绪"
            color = "#FFD700" 
        elif evt['type'] == "IDLE":
            msg = f"[T={t}ms] 💤 <b>系统空闲</b>: CPU 进入低功耗模式。"
            color = "#808080"
        elif evt['type'] == "TASK_FINISH":
            msg = f"[T={t}ms] 🎉 <b>任务完成</b>: P{evt['prev_pid']} 执行完毕。"
            color = "#9370DB" 

        if msg:
            self.log_text.append(f"<span style='color:{color}'>{msg}</span>")
            sb = self.log_text.verticalScrollBar()
            sb.setValue(sb.maximum())
    
    def update_state(self):
        for r, val in cpu_registers.items():
            if r in self.reg_labels:
                self.reg_labels[r].setText(val)

# === 主类 ===
class QtRTOSimeline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        ctrl_panel = QWidget()
        ctrl_layout = QHBoxLayout(ctrl_panel)
        
        self.btn_irq = QPushButton("⚡ 模拟外部硬件中断 (Interrupt)")
        self.btn_irq.setStyleSheet("background-color: #C0392B; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.btn_irq.clicked.connect(lambda: trigger_external_interrupt(99))
        ctrl_layout.addWidget(self.btn_irq)
        ctrl_layout.addStretch()
        main_layout.addWidget(ctrl_panel)

        self.analyzer = RTOSLogicAnalyzer()
        main_layout.addWidget(self.analyzer, 2)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        tcb_group = QGroupBox("任务控制块 (TCB)")
        tcb_layout = QVBoxLayout(tcb_group)
        self.tcb_table = QTableWidget()
        self.tcb_table.setColumnCount(4)
        self.tcb_table.setHorizontalHeaderLabels(["PID", "优先级", "状态", "说明"])
        self.tcb_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tcb_layout.addWidget(self.tcb_table)
        bottom_splitter.addWidget(tcb_group)

        self.cpu_panel = CpuStatePanel()
        bottom_splitter.addWidget(self.cpu_panel)
        
        bottom_splitter.setSizes([350, 550])
        main_layout.addWidget(bottom_splitter, 1)
        
        self.do_reset()

    def do_reset(self):
        reset_rtos_data() 
        self.analyzer.update_data([])
        self.cpu_panel.reset() 
        self.tcb_table.setRowCount(0)
    
    def reset_simulation(self):
        self.do_reset()

    def update_timeline(self, data):
        self.analyzer.update_data(data)
        self.cpu_panel.update_state()
        self.cpu_panel.update_log(data) 
        
        tasks = list(STATUS.all_processes.values())
        tasks.sort(key=lambda x: (not getattr(x, 'is_isr', False), x.priority))
        
        self.tcb_table.setRowCount(len(tasks))
        for i, t in enumerate(tasks):
            pid_item = QTableWidgetItem(str(t.pid))
            if getattr(t, 'is_isr', False):
                pid_item.setText(f"{t.pid} (ISR)")
            
            self.tcb_table.setItem(i, 0, pid_item)
            self.tcb_table.setItem(i, 1, QTableWidgetItem(str(t.priority)))
            
            state_str = t.state.value
            if getattr(t, 'is_isr', False) and t.state == ProcessState.RUNNING:
                state_str = "RUNNING (ISR)"
            
            self.tcb_table.setItem(i, 2, QTableWidgetItem(state_str))
            
            reason = getattr(t, 'block_reason', '-')
            if getattr(t, 'is_isr', False): reason = "Hard IRQ"
            self.tcb_table.setItem(i, 3, QTableWidgetItem(reason))