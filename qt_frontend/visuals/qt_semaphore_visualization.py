# qt_frontend/visuals/qt_semaphore_visualization.py
# OS 信号量可视化 — 修复版（包含读者/写者策略 + 最大读者/写者数）
# 2025-xx-xx - 集成修复与增强

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QComboBox, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsPathItem, QGraphicsItem,
    QSpinBox, QTextEdit, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QLineF
from PyQt6.QtGui import (
    QBrush, QPen, QColor, QFont, QPainter, QPainterPath, 
    QRadialGradient
)
import random
import math
import time

# === 主题色彩 ===
C_BG        = QColor("#FFFFFF")
C_PANEL     = QColor("#F8F9FA")
C_GRID      = QColor("#E9ECEF")
C_ACCENT    = QColor("#0284C7")
C_WARN      = QColor("#F59E0B")
C_OK        = QColor("#10B981")
C_DANGER    = QColor("#EF4444")
C_TEXT_MAIN = QColor("#1F2937")
C_TEXT_SUB  = QColor("#6B7280")

class AnimatedGraphicsItem:
    def __init__(self):
        self.target_pos = None
        self.current_pos = None
        self.speed = 0.15

    def set_target(self, pos):
        self.target_pos = pos

    def update_animation(self):
        if self.target_pos is not None and self.current_pos is not None:
            dx = self.target_pos.x() - self.current_pos.x()
            dy = self.target_pos.y() - self.current_pos.y()
            if abs(dx) < 0.5 and abs(dy) < 0.5:
                self.current_pos = self.target_pos
            else:
                new_x = self.current_pos.x() + dx * self.speed
                new_y = self.current_pos.y() + dy * self.speed
                self.current_pos = QPointF(new_x, new_y)
            self.setPos(self.current_pos)

class NeonSemaphore(QGraphicsEllipseItem):
    def __init__(self, x, y, name, initial_value):
        radius = 35
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.setPos(x, y)
        self.value = initial_value
        self.name = name
        self.setPen(QPen(QColor("#CBD5E1"), 3))
        self.lbl_name = QGraphicsTextItem(name, self)
        self.lbl_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_name.setDefaultTextColor(C_TEXT_SUB)
        r = self.lbl_name.boundingRect()
        self.lbl_name.setPos(-r.width()/2, -radius - 25)
        self.lbl_val = QGraphicsTextItem(str(self.value), self)
        self.lbl_val.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self.update_color()

    def update_value(self, val):
        self.value = val
        self.lbl_val.setPlainText(str(val))
        self.update_color()

    def update_color(self):
        grad = QRadialGradient(0, 0, 40)
        if self.value > 0:
            grad.setColorAt(0, C_OK)
            grad.setColorAt(1, QColor("#059669"))
            self.lbl_val.setDefaultTextColor(QColor("#FFFFFF"))
        else:
            grad.setColorAt(0, C_DANGER)
            grad.setColorAt(1, QColor("#B91C1C"))
            self.lbl_val.setDefaultTextColor(QColor("#FFFFFF"))
        self.setBrush(QBrush(grad))
        r = self.lbl_val.boundingRect()
        self.lbl_val.setPos(-r.width()/2, -r.height()/2)

class ForkItem(QGraphicsLineItem, AnimatedGraphicsItem):
    def __init__(self, table_pos):
        QGraphicsLineItem.__init__(self, -15, 0, 15, 0)
        AnimatedGraphicsItem.__init__(self)
        self.table_pos = table_pos
        self.current_pos = table_pos
        self.setPos(table_pos)
        pen = QPen(C_WARN, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)
        self.base_rotation = 0

    def set_rotation_angle(self, angle):
        self.setRotation(angle)
        self.base_rotation = angle

class ReaderBall(QGraphicsEllipseItem, AnimatedGraphicsItem):
    def __init__(self, start_pos, target_pos, callback_done=None):
        QGraphicsEllipseItem.__init__(self, -10, -10, 20, 20)
        AnimatedGraphicsItem.__init__(self)
        self.current_pos = start_pos
        self.setPos(start_pos)
        self.set_target(target_pos)
        self.callback_done = callback_done
        self.state = "entering"
        self.setBrush(QBrush(C_ACCENT))
        self.setPen(QPen(Qt.GlobalColor.white, 2))

    def update_animation(self):
        super().update_animation()
        if self.state == "entering" and self.pos() == self.target_pos:
            self.state = "reading"
        elif self.state == "leaving" and self.pos() == self.target_pos:
            if self.callback_done:
                self.callback_done(self)

class QtSemaphoreVisualization(QWidget):
    def __init__(self):
        super().__init__()
        self.current_model = "producer_consumer"
        self.simulation_running = False
        self.logic_timer = QTimer(self)
        self.logic_timer.timeout.connect(self.run_logic_step)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animations)
        self.anim_timer.start(16)
        self.state = self.create_initial_state()
        self.init_ui()
        self.draw_producer_consumer()
        # 默认隐藏读者-写者模型专用控件
        self.rw_controls_container.hide()

    def create_initial_state(self):
        return {
            "buffer": [0]*5,
            "semaphores": {},
            "blocked_queue": [],
            "blocked_requests": [],
            "req_seq": 0,
            "philosophers": [0]*5,
            "fork_owners": [None]*5,
            "fork_returning": [False]*5,
            "readers": [],
            "writer_active": False,
            "writer_timer": 0,
            "resource_request_queue": []
        }

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        stage_widget = QWidget()
        stage_widget.setStyleSheet(f"background-color: {C_BG.name()};")
        stage_layout = QVBoxLayout(stage_widget)

        top_bar = QHBoxLayout()
        self.combo_model = QComboBox()
        self.combo_model.addItems(["生产者-消费者模型", "读者-写者模型", "哲学家就餐问题"])
        self.combo_model.currentIndexChanged.connect(self.change_model)
        self.combo_model.setStyleSheet("""
            QComboBox { padding: 6px; font-size: 14px; background: #F1F5F9; color: #1F2937; border: 1px solid #CBD5E1; border-radius: 4px; }
            QComboBox::drop-down { border: none; }
        """)

        self.btn_control = QPushButton("开始模拟")
        self.btn_control.clicked.connect(self.toggle_simulation)
        self.btn_control.setStyleSheet("""
            QPushButton { background: #0284C7; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; border: none; }
            QPushButton:hover { background: #0369A1; }
        """)

        self.btn_reset = QPushButton("重置")
        self.btn_reset.clicked.connect(self.reset_simulation)
        self.btn_reset.setStyleSheet("""
            QPushButton { background: #E2E8F0; color: #334155; padding: 6px 15px; border-radius: 4px; border: none; }
            QPushButton:hover { background: #CBD5E1; }
        """)

        top_bar.addWidget(QLabel("选择模型: "))
        top_bar.addWidget(self.combo_model)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_control)
        top_bar.addWidget(self.btn_reset)
        stage_layout.addLayout(top_bar)

        self.scene = QGraphicsScene(0, 0, 800, 500)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setStyleSheet("border: none; background: transparent;")
        stage_layout.addWidget(self.view)

        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet("color: #64748B; font-family: Consolas;")
        stage_layout.addWidget(self.lbl_status)

        main_layout.addWidget(stage_widget, stretch=7)

        panel = QWidget()
        panel.setStyleSheet(f"background-color: {C_PANEL.name()}; border-left: 1px solid #E2E8F0;")
        panel.setFixedWidth(320)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)

        panel_layout.addWidget(QLabel("模拟速度 (ms):"))
        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(200, 3000)
        self.spin_speed.setValue(1000)
        self.spin_speed.valueChanged.connect(lambda v: self.logic_timer.setInterval(v))
        self.spin_speed.setStyleSheet("background: white; color: #333; padding: 5px; border: 1px solid #CBD5E1; border-radius: 4px;")
        panel_layout.addWidget(self.spin_speed)

        # 创建一个容器用于存放读者-写者模型专用控件
        self.rw_controls_container = QWidget()
        rw_controls_layout = QVBoxLayout(self.rw_controls_container)
        rw_controls_layout.setContentsMargins(0, 0, 0, 0)
        rw_controls_layout.setSpacing(10)

        rw_controls_layout.addWidget(QLabel("读写策略:"))
        self.combo_rw_strategy = QComboBox()
        self.combo_rw_strategy.addItems(["读者优先", "写者优先", "读写公平"])
        self.combo_rw_strategy.setCurrentIndex(0)
        self.combo_rw_strategy.setToolTip("选择读写优先策略：读者优先 / 写者优先 / 读写公平（先到先服务）")
        rw_controls_layout.addWidget(self.combo_rw_strategy)

        # === 新增：最大读者/写者数设置 ===
        rw_controls_layout.addWidget(QLabel("最大读者数:"))
        self.spin_max_readers = QSpinBox()
        self.spin_max_readers.setRange(1, 50)
        self.spin_max_readers.setValue(10)
        rw_controls_layout.addWidget(self.spin_max_readers)

        rw_controls_layout.addWidget(QLabel("最大写者数:"))
        self.spin_max_writers = QSpinBox()
        self.spin_max_writers.setRange(1, 50)
        self.spin_max_writers.setValue(5)
        rw_controls_layout.addWidget(self.spin_max_writers)

        # 将容器添加到主面板布局
        panel_layout.addWidget(self.rw_controls_container)

        panel_layout.addWidget(QLabel("系统日志:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background: white; color: #333; font-family: Consolas; font-size: 11px; border: 1px solid #CBD5E1; border-radius: 4px;")
        panel_layout.addWidget(self.txt_log)

        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #475569; font-size: 12px; margin-top: 10px; font-weight: 500;")
        panel_layout.addWidget(self.lbl_desc)

        main_layout.addWidget(panel, stretch=3)

# ---------------- 第 2 段 ----------------
    def init_scene_background(self):
        self.scene.clear()
        self.visual_items = {}
        self.sem_items = {}
        pen = QPen(C_GRID, 1)
        pen.setStyle(Qt.PenStyle.SolidLine)
        for x in range(0, 801, 50): self.scene.addLine(x, 0, x, 500, pen)
        for y in range(0, 501, 50): self.scene.addLine(0, y, 800, y, pen)

    def draw_producer_consumer(self):
        self.init_scene_background()
        self.state = self.create_initial_state()
        self.state["semaphores"] = {"mutex":1, "empty":5, "full":0}
        self.lbl_desc.setText("【生产者-消费者】\n\n工厂(左)生产数据块，放入传送带。消费者(右)取走。")
        sx, sy = 220, 200
        belt = QGraphicsRectItem(sx-10, sy, 380, 70)
        belt.setBrush(QBrush(C_PANEL))
        belt.setPen(QPen(QColor("#CBD5E1"), 2))
        self.scene.addItem(belt)
        self.visual_items["slots"] = []
        for i in range(5):
            slot = QGraphicsRectItem(sx + i*75, sy+10, 50, 50)
            slot.setBrush(QBrush(QColor("white")))
            slot.setPen(QPen(QColor("#CBD5E1"), 1))
            self.scene.addItem(slot)
            self.visual_items["slots"].append(slot)
            txt = QGraphicsTextItem(str(i))
            txt.setDefaultTextColor(C_TEXT_SUB)
            txt.setPos(sx + i*75 + 18, sy+70)
            self.scene.addItem(txt)
        self.sem_items["mutex"] = NeonSemaphore(410, 380, "mutex", 1)
        self.sem_items["empty"] = NeonSemaphore(280, 380, "empty", 5)
        self.sem_items["full"]  = NeonSemaphore(540, 380, "full", 0)
        for s in self.sem_items.values(): self.scene.addItem(s)
        t1 = self.scene.addText("PRODUCER")
        t1.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        t1.setDefaultTextColor(C_ACCENT)
        t1.setPos(40, 215)
        t2 = self.scene.addText("CONSUMER")
        t2.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        t2.setDefaultTextColor(C_WARN)
        t2.setPos(640, 215)
        self.draw_blocked_area(100, 450)

    def draw_reader_writer(self):
        self.init_scene_background()
        self.state = self.create_initial_state()
        self.state["semaphores"] = {"rw_mutex":1, "mutex":1}
        # 初始化读者计数器（虽然不再直接使用，但为了兼容现有代码保留）
        self.state["read_count"] = 0
        self.lbl_desc.setText("【读者-写者】\n\n可在右侧选择读写优先策略：读者优先 / 写者优先 / 读写公平。")
        lib_rect = QGraphicsRectItem(250, 100, 300, 200)
        self.visual_items["library"] = lib_rect
        lib_rect.setBrush(QBrush(QColor(2, 132, 199, 30)))
        lib_rect.setPen(QPen(C_ACCENT, 2, Qt.PenStyle.DashLine))
        self.scene.addItem(lib_rect)
        txt = self.scene.addText("SHARED DATABASE")
        txt.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        txt.setDefaultTextColor(C_ACCENT)
        text_width = txt.boundingRect().width()
        txt.setPos(400 - text_width/2, 190)
        tr = self.scene.addText("Readers Entry")
        tr.setPos(50, 150)
        tr.setDefaultTextColor(C_ACCENT)
        tr.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        tw = self.scene.addText("Writers Entry")
        tw.setPos(650, 150)
        tw.setDefaultTextColor(C_DANGER)
        tw.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.sem_items["mutex"] = NeonSemaphore(250, 400, "mutex", 1)
        self.sem_items["rw_mutex"] = NeonSemaphore(550, 400, "rw_mutex", 1)
        for s in self.sem_items.values(): self.scene.addItem(s)
        self.lbl_rc = QGraphicsTextItem("Read Count: 0")
        self.lbl_rc.setFont(QFont("Consolas", 14))
        self.lbl_rc.setDefaultTextColor(C_TEXT_MAIN)
        self.lbl_rc.setPos(320, 310)
        self.scene.addItem(self.lbl_rc)
        self.draw_blocked_area(100, 450)

    def draw_philosophers(self):
        self.init_scene_background()
        self.state = self.create_initial_state()
        self.state["fork_owners"] = [None] * 5
        self.lbl_desc.setText("【哲学家就餐】\n\n观察叉子的移动。")
        cx, cy = 400, 250
        radius = 140
        table = QGraphicsEllipseItem(cx-radius, cy-radius, radius*2, radius*2)
        table.setBrush(QBrush(QColor("#FEF3C7")))
        table.setPen(QPen(C_WARN, 3))
        self.scene.addItem(table)
        self.visual_items["phils"] = []
        self.visual_items["forks"] = []
        self.phil_pos = []
        self.fork_table_pos = []
        for i in range(5):
            angle = i * 72 - 90
            rad = math.radians(angle)
            px = cx + 190 * math.cos(rad)
            py = cy + 190 * math.sin(rad)
            self.phil_pos.append(QPointF(px, py))
            f_angle = angle + 36
            f_rad = math.radians(f_angle)
            fx = cx + 110 * math.cos(f_rad)
            fy = cy + 110 * math.sin(f_rad)
            self.fork_table_pos.append(QPointF(fx, fy))
            p_circle = QGraphicsEllipseItem(px-30, py-30, 60, 60)
            p_circle.setBrush(QBrush(C_PANEL))
            p_circle.setPen(QPen(C_GRID, 2))
            self.scene.addItem(p_circle)
            p_txt = QGraphicsTextItem(f"P{i}")
            p_txt.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            p_txt.setPos(px-12, py-12)
            self.scene.addItem(p_txt)
            status_txt = QGraphicsTextItem("Thinking")
            status_txt.setFont(QFont("Arial", 8))
            status_txt.setDefaultTextColor(C_TEXT_SUB)
            status_txt.setPos(px-25, py+35)
            self.scene.addItem(status_txt)
            self.visual_items["phils"].append((p_circle, status_txt))
            fork = ForkItem(QPointF(fx, fy))
            fork.set_rotation_angle(f_angle + 90)
            self.scene.addItem(fork)
            self.visual_items["forks"].append(fork)

    def draw_blocked_area(self, x, y):
        area = QGraphicsRectItem(x, y, 600, 50)
        area.setBrush(QBrush(C_PANEL))
        area.setPen(QPen(C_GRID, 1, Qt.PenStyle.DashLine))
        self.scene.addItem(area)
        lbl = self.scene.addText("BLOCKED QUEUE (阻塞等待区)")
        lbl.setDefaultTextColor(C_TEXT_SUB)
        lbl.setPos(x+5, y+2)
        self.visual_items["blocked_start_pos"] = QPointF(x+180, y+12)

# ---------------- 第 3 段 ----------------
    def run_logic_step(self):
        if self.current_model == "producer_consumer":
            self.step_producer_consumer()
        elif self.current_model == "reader_writer":
            self.step_reader_writer()
        elif self.current_model == "philosopher_dining":
            self.step_philosophers()
        self.update_common_ui()

    def update_common_ui(self):
        for k, v in self.state["semaphores"].items():
            if k in self.sem_items:
                self.sem_items[k].update_value(v)
        for item in self.scene.items():
            if hasattr(item, "is_blocked_viz"):
                self.scene.removeItem(item)
        if self.current_model != "philosopher_dining":
            base = self.visual_items.get("blocked_start_pos", QPointF(0,0))
            # 使用真实的请求信息而不是简化的blocked_queue
            blocked_requests = self.state["blocked_requests"]
            for i, req in enumerate(blocked_requests):
                color = C_DANGER if req["type"] == "Writer" else C_ACCENT
                # 创建阻塞方块
                rect = QGraphicsRectItem(base.x() + i*30, base.y(), 24, 24)
                rect.setBrush(QBrush(color))
                rect.setPen(QPen(Qt.GlobalColor.white))
                rect.is_blocked_viz = True
                self.scene.addItem(rect)
                # 创建请求标签
                label = QGraphicsTextItem(req["type"][0])  # 只显示R或W
                label.setFont(QFont("Consolas", 12))
                label.setDefaultTextColor(Qt.GlobalColor.white)
                # 计算标签位置，使其居中显示在方块内
                label_bounds = label.boundingRect()
                label_x = base.x() + i*30 + (24 - label_bounds.width()) / 2
                label_y = base.y() + (24 - label_bounds.height()) / 2
                label.setPos(label_x, label_y)
                label.is_blocked_viz = True
                self.scene.addItem(label)

    # --- 生产者/消费者 ---
    def step_producer_consumer(self):
        sem = self.state["semaphores"]
        buf = self.state["buffer"]
        action = random.choice(["produce", "consume", "idle"])
        if action == "produce":
            if sem["empty"] > 0:
                if sem["mutex"] > 0:
                    sem["mutex"] -= 1
                    sem["empty"] -= 1
                    for i in range(5):
                        if buf[i] == 0:
                            buf[i] = 1
                            self.visual_items["slots"][i].setBrush(QBrush(C_OK))
                            self.log(f"生产 -> Slot {i}")
                            break
                    sem["mutex"] += 1
                    sem["full"] += 1
                else:
                    self.add_blocked("Prod")
            else:
                self.add_blocked("Prod")
        elif action == "consume":
            if sem["full"] > 0:
                if sem["mutex"] > 0:
                    sem["mutex"] -= 1
                    sem["full"] -= 1
                    for i in range(5):
                        if buf[i] == 1:
                            buf[i] = 0
                            self.visual_items["slots"][i].setBrush(QBrush(QColor("white")))
                            self.log(f"消费 <- Slot {i}")
                            break
                    sem["mutex"] += 1
                    sem["empty"] += 1
                    self.pop_blocked("Prod")
                else:
                    self.add_blocked("Cons")
            else:
                self.add_blocked("Cons")
        if sem["mutex"] == 1:
            if sem["empty"] > 0: self.pop_blocked("Prod")
            if sem["full"] > 0: self.pop_blocked("Cons")

    # --- 读写辅助管理（新增） ---
    def _get_strategy(self):
        txt = self.combo_rw_strategy.currentText()
        if txt == "写者优先": return "writer_priority"
        if txt == "读写公平": return "fair"
        return "reader_priority"

    def add_blocked(self, name):
        if len(self.state["blocked_queue"]) < 10:
            self.state["blocked_queue"].append(name)

    def add_blocked_request(self, req_type):
        seq = self.state.get("req_seq", 0) + 1
        self.state["req_seq"] = seq
        label = f"{req_type}-{seq}"
        if len(self.state["blocked_queue"]) < 10:
            self.state["blocked_queue"].append(req_type)
        self.state["blocked_requests"].append({
            "type": req_type,
            "seq": seq,
            "label": label,
            "time": time.time()
        })
        self.log(f"加入阻塞请求: {label}")
        return label

    def remove_blocked_request_by_label(self, label):
        br = self.state["blocked_requests"]
        for i, r in enumerate(br):
            if r["label"] == label:
                br.pop(i)
                prefix = r["type"]
                if prefix in self.state["blocked_queue"]:
                    self.state["blocked_queue"].remove(prefix)
                return True
        return False

    def pop_first_blocked_of_type(self, req_type):
        br = self.state["blocked_requests"]
        for i, r in enumerate(br):
            if r["type"] == req_type:
                req = br.pop(i)
                if req_type in self.state["blocked_queue"]:
                    self.state["blocked_queue"].remove(req_type)
                return req
        return None

    def wake_next_on_resource_free(self):
        strategy = self._get_strategy()
        br = self.state["blocked_requests"]
        if not br:
            return
        if strategy == "fair":
            br.sort(key=lambda x: x["seq"])
            head = br[0]
            if head["type"] == "Writer":
                # 检查当前是否有活跃读者
                active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
                if active_readers_count == 0:
                    req = self.pop_first_blocked_of_type("Writer")
                    if req:
                        self._start_writer_from_request(req)
            else:
                # 计算当前活跃读者数量
                active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
                max_r = self.spin_max_readers.value()
                available_slots = max_r - active_readers_count
                
                readers_to_wake = []
                br_sorted = sorted(self.state["blocked_requests"], key=lambda x: x["seq"])
                for r in br_sorted:
                    if r["type"] == "Reader":
                        if available_slots > 0:
                            readers_to_wake.append(r)
                            available_slots -= 1
                    else:
                        break
                for r in readers_to_wake:
                    self.remove_blocked_request_by_label(r["label"])
                    self.spawn_reader(True, from_block=True, request_label=r["label"])
            return
        if strategy == "writer_priority":
            if any(r["type"] == "Writer" for r in br):
                req = self.pop_first_blocked_of_type("Writer")
                if req:
                    self._start_writer_from_request(req)
                return
            else:
                # 计算当前活跃读者数量
                active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
                max_r = self.spin_max_readers.value()
                available_slots = max_r - active_readers_count
                
                readers = [r for r in sorted(br, key=lambda x: x["seq"]) if r["type"] == "Reader"]
                # 只唤醒可以容纳的读者数量
                readers_to_wake = readers[:available_slots]
                for r in readers_to_wake:
                    self.remove_blocked_request_by_label(r["label"])
                    self.spawn_reader(True, from_block=True, request_label=r["label"])
                return
        if strategy == "reader_priority":
            # 计算当前活跃读者数量
            active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
            max_r = self.spin_max_readers.value()
            
            if active_readers_count > 0:
                # 有活跃读者，按照读者优先策略，唤醒尽可能多的读者，但不超过最大读者数
                readers = [r for r in sorted(br, key=lambda x: x["seq"]) if r["type"] == "Reader"]
                available_slots = max_r - active_readers_count
                
                if available_slots > 0:
                    # 只唤醒可以容纳的读者数量
                    readers_to_wake = readers[:available_slots]
                    for r in readers_to_wake:
                        self.remove_blocked_request_by_label(r["label"])
                        self.spawn_reader(True, from_block=True, request_label=r["label"])
                return
            else:
                if self.state.get("writer_active", False):
                    return
                
                # 没有活跃读者，先检查是否有读者等待
                readers = [r for r in sorted(br, key=lambda x: x["seq"]) if r["type"] == "Reader"]
                if readers:
                    # 唤醒尽可能多的读者，但不超过最大读者数
                    available_slots = max_r
                    readers_to_wake = readers[:available_slots]
                    for r in readers_to_wake:
                        self.remove_blocked_request_by_label(r["label"])
                        self.spawn_reader(True, from_block=True, request_label=r["label"])
                    return
                
                # 没有读者等待，唤醒写者
                if any(r["type"] == "Writer" for r in br):
                    req = self.pop_first_blocked_of_type("Writer")
                    if req:
                        self._start_writer_from_request(req)
                return

    def _start_writer_from_request(self, req):
        sem = self.state["semaphores"]
        if sem.get("rw_mutex", 1) > 0 and not self.state.get("writer_active", False):
            sem["rw_mutex"] = 0
            self.state["writer_active"] = True
            self.state["writer_timer"] = 3
            if "library" in self.visual_items:
                self.visual_items["library"].setBrush(QBrush(QColor(239, 68, 68, 40)))
            self.log(f"唤醒写者 {req['label']} 开始写入")
            return True
        else:
            return False

    def spawn_reader(self, success, from_block=False, request_label=None):
        if not success:
            if not from_block:
                self.add_blocked_request("Reader")
            else:
                pass
            return

        # 再次检查当前活跃读者数量是否已经超过最大读者数
        max_r = self.spin_max_readers.value()
        active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
        if active_readers_count >= max_r:
            # 如果已经超过最大读者数，将请求重新添加到阻塞队列中（如果是从阻塞队列唤醒的请求）
            if from_block and request_label:
                self.add_blocked_request("Reader")
                self.log(f"读者 {request_label} 唤醒失败，已达到最大读者数限制")
            return

        def on_done(b):
            if b in self.state["readers"]:
                self.state["readers"].remove(b)
            try:
                self.scene.removeItem(b)
            except:
                pass
            # === 修复点：使用正确函数名 ===
            self.rearrange_readers_positions()

        ball = ReaderBall(QPointF(50, 150), QPointF(310, 130))
        ball.callback_done = on_done
        self.scene.addItem(ball)
        self.state["readers"].append(ball)
        # 不再直接使用独立计数器，而是基于实际读者数量
        pass
        self.log(f"读者进入 {'(被唤醒:'+request_label+')' if from_block and request_label else ''}")
        self.rearrange_readers_positions()

    def rearrange_readers_positions(self):
        active_readers = [b for b in self.state["readers"] if b.state != "leaving"]
        for i, reader in enumerate(active_readers):
            rows = i // 5
            cols = i % 5
            target_x = 310 + cols * 40
            target_y = 130 + rows * 35
            reader.set_target(QPointF(target_x, target_y))

# ---------------- 第 4 段 ----------------
    def step_reader_writer(self):
        sem = self.state["semaphores"]
        r = random.random()

        # 读者到达（30%）
        if r < 0.3:
            strategy = self._get_strategy()
            # 最大读者限制
            max_r = self.spin_max_readers.value()
            # 计算当前活跃读者数量
            active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
            if active_readers_count >= max_r:
                self.add_blocked_request("Reader")
                self.log("读者达到最大上限，被阻塞")
                return

            if sem["mutex"] > 0:
                sem["mutex"] = 0
                can_enter = False
                if strategy == "reader_priority":
                    if self.state.get("writer_active", False):
                        can_enter = False
                    else:
                        # 计算当前活跃读者数量
                        active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
                        if sem.get("rw_mutex", 1) == 0 and active_readers_count > 0:
                            can_enter = True
                        else:
                            if sem.get("rw_mutex", 1) > 0:
                                can_enter = True
                            else:
                                can_enter = False
                elif strategy == "writer_priority":
                    writers_waiting = any(req["type"] == "Writer" for req in self.state["blocked_requests"])
                    if self.state.get("writer_active", False) or writers_waiting or sem.get("rw_mutex", 1) == 0:
                        can_enter = False
                    else:
                        can_enter = True
                else: # fair
                    hypothetical_seq = self.state.get("req_seq", 0) + 1
                    earliest_writer_seq = None
                    for req in self.state["blocked_requests"]:
                        if req["type"] == "Writer":
                            if earliest_writer_seq is None or req["seq"] < earliest_writer_seq:
                                earliest_writer_seq = req["seq"]
                    if earliest_writer_seq is not None and earliest_writer_seq < hypothetical_seq:
                        can_enter = False
                    else:
                        if self.state.get("writer_active", False):
                            can_enter = False
                        else:
                            can_enter = True

                if can_enter:
                    # 计算当前活跃读者数量
                    active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
                    if active_readers_count == 0:
                        if sem.get("rw_mutex", 1) > 0:
                            sem["rw_mutex"] = 0
                    self.spawn_reader(True)
                    # 计算新的活跃读者数量（加1）
                    new_active_readers_count = active_readers_count + 1
                    self.log(f"读者进入 (第{new_active_readers_count}位)")
                else:
                    self.add_blocked_request("Reader")
                    self.log("读者被阻塞 (加入等待队列)")
                sem["mutex"] = 1
            else:
                self.add_blocked_request("Reader")
                self.log("读者被阻塞 (mutex 不可用)")

        # 读者离开（20%）
        elif r < 0.5:
            # 计算当前活跃读者数量
            active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
            if active_readers_count > 0:
                if sem["mutex"] > 0:
                    sem["mutex"] = 0
                    active_readers = [b for b in self.state["readers"] if b.state == "reading"]
                    if active_readers:
                        b = active_readers[0]
                        b.state = "leaving"
                        b.set_target(QPointF(800, 150))
                        # 计算离开后的活跃读者数量
                        new_active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"]) - 1
                        if new_active_readers_count <= 0:
                            sem["rw_mutex"] = 1
                            self.log("最后一位读者离开")
                        # 无论是否是最后一位读者离开，都检查是否有等待的读者可以唤醒
                        self.wake_next_on_resource_free()
                    sem["mutex"] = 1

        # 写者尝试（20%）
        elif r < 0.7:
            strategy = self._get_strategy()
            # 最大写者限制（包括正在写的和队列中的写者）
            max_w = self.spin_max_writers.value()
            current_writers = (1 if self.state.get("writer_active", False) else 0) + \
                              sum(1 for rr in self.state["blocked_requests"] if rr["type"] == "Writer")
            if current_writers < max_w:
                # 只有当当前写者数（包括正在写的和队列中的）小于最大写者数时，才允许新的写者请求
                if sem.get("rw_mutex", 1) > 0 and not self.state.get("writer_active", False):
                    allow_writer_now = True
                    if strategy == "fair":
                        hypothetical_seq = self.state.get("req_seq", 0) + 1
                        earlier_reader = any(req["type"] == "Reader" and req["seq"] < hypothetical_seq for req in self.state["blocked_requests"])
                        if earlier_reader:
                            allow_writer_now = False
                    # 计算当前活跃读者数量
                    active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
                    if allow_writer_now and active_readers_count == 0:
                        sem["rw_mutex"] = 0
                        self.state["writer_active"] = True
                        self.state["writer_timer"] = 3
                        if "library" in self.visual_items:
                            self.visual_items["library"].setBrush(QBrush(QColor(239, 68, 68, 40)))
                        self.log("写者正在写入...")
                    else:
                        label = self.add_blocked_request("Writer")
                        self.log(f"写者被阻塞 (加入等待队列: {label})")
                else:
                    label = self.add_blocked_request("Writer")
                    self.log(f"写者被阻塞 (加入等待队列: {label})")
            else:
                self.log(f"写者达到最大上限 ({current_writers}/{max_w})，拒绝新的写者请求")
                return

        # 写者处理（计时）
        if self.state.get("writer_active", False):
            self.state["writer_timer"] -= 1
            if self.state["writer_timer"] <= 0:
                self.state["writer_active"] = False
                sem["rw_mutex"] = 1
                if "library" in self.visual_items:
                    self.visual_items["library"].setBrush(QBrush(QColor(2, 132, 199, 30)))
                self.log("写者离开")
                self.wake_next_on_resource_free()

        # 计算实际活跃的读者数量（与小蓝圈数量一致）
        active_readers_count = len([b for b in self.state["readers"] if b.state != "leaving"])
        self.lbl_rc.setPlainText(f"Read Count: {active_readers_count}")

    # --- 哲学家模型 ---
    def step_philosophers(self):
        owners = self.state["fork_owners"]
        fork_returning = self.state["fork_returning"]
        request_queue = self.state["resource_request_queue"]
        for pid in range(5):
            if self.state["philosophers"][pid] == 2:
                left_fork = (pid + 4) % 5
                right_fork = pid
                if random.random() < 0.4:
                    fork_returning[left_fork] = True
                    fork_returning[right_fork] = True
                    self.state["philosophers"][pid] = 0
                    self.update_phil_visual(pid, 0)
                    self.visual_items["forks"][left_fork].set_target(self.fork_table_pos[left_fork])
                    self.visual_items["forks"][right_fork].set_target(self.fork_table_pos[right_fork])
                    left_fork_angle = (left_fork + 0.5) * 72 - 90 + 90
                    right_fork_angle = (right_fork + 0.5) * 72 - 90 + 90
                    self.visual_items["forks"][left_fork].set_rotation_angle(left_fork_angle)
                    self.visual_items["forks"][right_fork].set_rotation_angle(right_fork_angle)
                    self.log(f"P{pid} 吃完了，开始归还左右两边的叉子")
        thinking_pids = [pid for pid in range(5) if self.state["philosophers"][pid] == 0]
        if thinking_pids and random.random() < 0.5:
            pid = random.choice(thinking_pids)
            self.state["philosophers"][pid] = 1
            self.update_phil_visual(pid, 1)
            if pid not in request_queue:
                request_queue.append(pid)
                self.log(f"P{pid} 饿了，加入请求队列，当前队列: {request_queue}")
            else:
                self.log(f"P{pid} 饿了，已在请求队列中")
            self.try_to_eat(pid)
        self.check_queue_and_eat()

    def try_to_eat(self, pid):
        if self.state["philosophers"][pid] != 1:
            return False
        owners = self.state["fork_owners"]
        fork_returning = self.state["fork_returning"]
        left_fork = (pid + 4) % 5
        right_fork = pid
        if (owners[left_fork] is None and owners[right_fork] is None and 
            not fork_returning[left_fork] and not fork_returning[right_fork]):
            owners[left_fork] = pid
            owners[right_fork] = pid
            self.state["philosophers"][pid] = 2
            self.update_phil_visual(pid, 2)
            if pid in self.state["resource_request_queue"]:
                self.state["resource_request_queue"].remove(pid)
            cx, cy = self.phil_pos[pid].x(), self.phil_pos[pid].y()
            angle = pid * 72 - 90
            rad = math.radians(angle)
            offset_distance = 30
            left_x = cx - offset_distance * math.cos(rad)
            left_y = cy - offset_distance * math.sin(rad)
            right_x = cx + offset_distance * math.cos(rad)
            right_y = cy + offset_distance * math.sin(rad)
            left_x += 5 * math.sin(rad)
            left_y -= 5 * math.cos(rad)
            right_x -= 5 * math.sin(rad)
            right_y += 5 * math.cos(rad)
            self.visual_items["forks"][left_fork].set_target(QPointF(left_x, left_y))
            self.visual_items["forks"][right_fork].set_target(QPointF(right_x, right_y))
            left_fork_angle = angle - 90
            right_fork_angle = angle + 90
            self.visual_items["forks"][left_fork].set_rotation_angle(left_fork_angle)
            self.visual_items["forks"][right_fork].set_rotation_angle(right_fork_angle)
            self.log(f"P{pid} 拿到左右两边的叉子，开始吃饭，队列剩余: {self.state['resource_request_queue']}")
            return True
        return False

    def check_queue_and_eat(self):
        queue_copy = self.state["resource_request_queue"].copy()
        for pid in queue_copy:
            if self.try_to_eat(pid):
                break

    def update_phil_visual(self, pid, state_code):
        circle, txt = self.visual_items["phils"][pid]
        if state_code == 0:
            circle.setBrush(QBrush(C_PANEL))
            txt.setPlainText("Thinking")
        elif state_code == 1:
            circle.setBrush(QBrush(C_WARN))
            txt.setPlainText("Hungry")
        elif state_code == 2:
            circle.setBrush(QBrush(C_OK))
            txt.setPlainText("Eating")

    # --- 通用辅助 ---
    def add_blocked_simple(self, name):
        if len(self.state["blocked_queue"]) < 10:
            self.state["blocked_queue"].append(name)

    def pop_blocked(self, prefix):
        for item in self.state["blocked_queue"]:
            if item.startswith(prefix):
                self.state["blocked_queue"].remove(item)
                return True
        return False

    def log(self, msg):
        self.txt_log.append(f"> {msg}")
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def update_animations(self):
        for item in self.scene.items():
            if isinstance(item, AnimatedGraphicsItem):
                old_pos = item.current_pos
                item.update_animation()
                if isinstance(item, ForkItem):
                    fork_id = -1
                    for i, fork_item in enumerate(self.visual_items["forks"]):
                        if fork_item is item:
                            fork_id = i
                            break
                    if fork_id != -1:
                        if self.state["fork_returning"][fork_id]:
                            target_pos = self.fork_table_pos[fork_id]
                            if (abs(item.current_pos.x() - target_pos.x()) < 0.5 and 
                                abs(item.current_pos.y() - target_pos.y()) < 0.5):
                                self.state["fork_returning"][fork_id] = False
                                self.state["fork_owners"][fork_id] = None
                                self.log(f"叉子 {fork_id} 已归还到桌子上，现在可以被使用")
                                self.check_queue_and_eat()

    def change_model(self, idx):
        self.simulation_running = False
        self.logic_timer.stop()
        self.btn_control.setText("开始模拟")
        self.txt_log.clear()
        mods = ["producer_consumer", "reader_writer", "philosopher_dining"]
        self.current_model = mods[idx]
        if idx == 0: 
            self.draw_producer_consumer()
            self.rw_controls_container.hide()  # 隐藏读者-写者专用控件
        elif idx == 1:
            self.draw_reader_writer()
            self.state["blocked_requests"] = []
            self.state["blocked_queue"] = []
            self.state["req_seq"] = 0
            self.rw_controls_container.show()  # 显示读者-写者专用控件
        elif idx == 2: 
            self.draw_philosophers()
            self.rw_controls_container.hide()  # 隐藏读者-写者专用控件

    def toggle_simulation(self):
        if self.simulation_running:
            self.logic_timer.stop()
            self.btn_control.setText("开始模拟")
        else:
            self.logic_timer.start(self.spin_speed.value())
            self.btn_control.setText("暂停模拟")
        self.simulation_running = not self.simulation_running

    def reset_simulation(self):
        self.txt_log.clear()
        self.change_model(self.combo_model.currentIndex())

# 如果你在 main.py 里以模块形式 import 这个类并且手动启动 Qt，我们不需要 main guard 在此文件中。
# 以上为 qt_semaphore_visualization.py 的完整内容（分为 4 段）。
