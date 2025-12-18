# qt_frontend/visuals/qt_ipc_visualization.py
# 自定义IPC可视化动画组件

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem,
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QTextEdit,
    QSpinBox, QFormLayout, QGroupBox, QFrame, QComboBox
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QTimer, QTime, QPropertyAnimation, 
    QEasingCurve, QDateTime
)
from PyQt6.QtGui import (
    QBrush, QPen, QFont, QColor, QPainter, QLinearGradient, 
    QRadialGradient, QFontMetrics, QPalette
)
from src.system_status import STATUS

class QtIpcVisualization(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 核心参数配置
        self.produce_interval = 1000  # 生产间隔（毫秒）
        self.consume_interval = 1500  # 消费间隔（毫秒）
        self.max_queue_size = 5  # 队列最大容量
        
        # 生产者-消费者模型状态
        self.message_queue = []
        self.producer_running = False
        self.consumer_running = False
        self.producer_blocked = False
        self.consumer_blocked = False
        self.simulation_running = False
        
        # 存储消息项和位置信息
        self.message_items = []
        self.producer_pos = QPointF(100, 150)
        self.consumer_pos = QPointF(500, 150)
        self.queue_start_pos = QPointF(200, 150)
        self.queue_spacing = 60
        self.message_id = 1
        
        # 动画相关
        self.animations = []  # 存储动画信息 (item, start_pos, end_pos, start_time, duration)
        self.is_animating = False  # 动画状态标志
        self.last_queue_size = 0
        
        # 呼吸灯动画
        self.producer_breathing = False
        self.consumer_breathing = False
        self.queue_warning = False
        
        # 定时器
        self.producer_timer = QTimer()
        self.producer_timer.timeout.connect(self.produce_message)
        
        self.consumer_timer = QTimer()
        self.consumer_timer.timeout.connect(self.consume_message)
       # 启动动画定时器
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animations)
        self.animation_timer.setInterval(16)  # ~60 FPS
        
        # 启动呼吸灯定时器
        self.breathing_timer = QTimer()
        self.breathing_timer.timeout.connect(self.update_breathing_effect)
        self.breathing_timer.start(50)  # 20 FPS
        
        self.breathing_progress = 0
        
        # 初始化UI
        self.init_ui()
        
        # 记录初始时间
        self.start_time = QDateTime.currentDateTime()
        
    def init_ui(self):
        """初始化UI布局，实现现代化的生产者消费者可视化界面"""
        # 主布局 - 垂直布局，分为标题区、可视化区和控制区
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 1. 顶部标题区
        title_label = QLabel("消息队列")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px;")
        main_layout.addWidget(title_label)
        
        # 2. 状态显示区
        status_layout = QHBoxLayout()
        status_layout.setSpacing(20)
        
        # 生产者状态
        self.producer_status_label = QLabel()
        self.producer_status_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
        self.producer_status_label.setStyleSheet("color: #16a34a; padding: 8px 15px; border-radius: 20px; background-color: #dcfce7;")
        status_layout.addWidget(self.producer_status_label)
        
        # 队列状态
        self.queue_status_label = QLabel()
        self.queue_status_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
        self.queue_status_label.setStyleSheet("color: #f59e0b; padding: 8px 15px; border-radius: 20px; background-color: #fef3c7;")
        status_layout.addWidget(self.queue_status_label)
        
        # 消费者状态
        self.consumer_status_label = QLabel()
        self.consumer_status_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
        self.consumer_status_label.setStyleSheet("color: #3b82f6; padding: 8px 15px; border-radius: 20px; background-color: #dbeafe;")
        status_layout.addWidget(self.consumer_status_label)
        
        main_layout.addLayout(status_layout)
        
        # 3. 核心可视化区域 - 使用更现代的设计
        self.graphics_view = QGraphicsView()
        self.graphics_view.setFixedSize(1200, 400)  # 增大视图区域以匹配场景宽度
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.graphics_view.setStyleSheet("border: 2px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;")
        
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        main_layout.addWidget(self.graphics_view, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 删除重复的控制按钮，保留底部控制栏
        
        # 初始化场景
        self.init_scene()
        
        # 更新状态显示
        self.update_status_display()
        
        # 日志组件已删除，不再添加初始日志
        
    def init_scene(self):
        """初始化场景，绘制现代化的生产者消费者可视化界面"""
        self.scene.clear()
        
        # 设置场景大小以匹配图形视图 - 增大宽度以解决显示不完整问题
        scene_width = 1200
        scene_height = 400
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        
        # 初始化消息列表和历史记录
        self.messages = []  # 存储场景中的消息项
        self.message_items = []  # 存储所有消息项和文本
        
        # 更新位置信息 - 调整位置让内容更居中
        self.producer_pos = QPointF(305, 200)  # 生产者位置（居中布局）
        self.consumer_pos = QPointF(875, 200)  # 消费者位置（居中布局）
        self.queue_start_pos = QPointF(425, 200)  # 队列起始位置（居中布局）
        self.queue_spacing = 70  # 队列项间距
        
        # 绘制背景装饰
        self.draw_background()
        
        # 绘制生产者（绿色圆角矩形）
        producer_rect = QRectF(0, 0, 100, 80)
        self.producer_item = QGraphicsRectItem(producer_rect)
        self.producer_item.setBrush(QBrush(QColor(34, 197, 94), Qt.BrushStyle.SolidPattern))  # 绿色
        self.producer_item.setPen(QPen(QColor(16, 185, 129), 3))  # 深绿色边框
        self.producer_item.setPos(self.producer_pos - QPointF(50, 40))  # 居中定位
        self.producer_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)  # 不可移动
        self.scene.addItem(self.producer_item)
        
        # 生产者图标
        producer_icon = QGraphicsEllipseItem(0, 0, 30, 30)
        producer_icon.setBrush(QBrush(QColor(217, 249, 157), Qt.BrushStyle.SolidPattern))  # 浅绿色
        producer_icon.setPen(QPen(QColor(16, 185, 129), 2))  # 深绿色边框
        producer_icon.setPos(self.producer_pos - QPointF(15, 50))  # 图标位置
        self.scene.addItem(producer_icon)
        
        # 生产者文本
        producer_text = QGraphicsTextItem("生产者")
        producer_text.setDefaultTextColor(QColor(255, 255, 255))  # 白色字体，更明显
        producer_text.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        producer_text.setPos(self.producer_pos - QPointF(30, 0))
        self.scene.addItem(producer_text)
        
        # 绘制消费者（蓝色圆角矩形）
        consumer_rect = QRectF(0, 0, 100, 80)
        self.consumer_item = QGraphicsRectItem(consumer_rect)
        self.consumer_item.setBrush(QBrush(QColor(59, 130, 246), Qt.BrushStyle.SolidPattern))  # 蓝色
        self.consumer_item.setPen(QPen(QColor(37, 99, 235), 3))  # 深蓝色边框
        self.consumer_item.setPos(self.consumer_pos - QPointF(50, 40))  # 居中定位
        self.consumer_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)  # 不可移动
        self.scene.addItem(self.consumer_item)
        
        # 消费者图标
        consumer_icon = QGraphicsEllipseItem(0, 0, 30, 30)
        consumer_icon.setBrush(QBrush(QColor(191, 219, 254), Qt.BrushStyle.SolidPattern))  # 浅蓝色
        consumer_icon.setPen(QPen(QColor(37, 99, 235), 2))  # 深蓝色边框
        consumer_icon.setPos(self.consumer_pos - QPointF(15, 50))  # 图标位置
        self.scene.addItem(consumer_icon)
        
        # 消费者文本
        consumer_text = QGraphicsTextItem("消费者")
        consumer_text.setDefaultTextColor(QColor(255, 255, 255))  # 白色字体，更明显
        consumer_text.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        consumer_text.setPos(self.consumer_pos - QPointF(30, 0))
        self.scene.addItem(consumer_text)
        
        # 绘制消息队列区域
        self.draw_queue_area()
        
        # 更新状态显示
        self.update_status_display()
    
    def update_visualization(self, message_queue):
        """更新可视化效果"""
        current_size = len(message_queue)
        
        # 如果队列大小没有变化，不需要动画
        if current_size == self.last_queue_size:
            return
            
        # 创建新的消息项或移除多余的消息项
        if current_size > self.last_queue_size:
            # 有新消息产生
            self.animate_produce(message_queue[-1], current_size - 1)
        else:
            # 有消息被消费
            self.animate_consume(current_size)
        
        self.last_queue_size = current_size
        
    def toggle_simulation(self):
        """启动/暂停模拟"""
        if self.simulation_running:
            # 暂停
            self.simulation_running = False
            self.producer_timer.stop()
            self.consumer_timer.stop()
            
            # 更新生产者和消费者状态为已停止
            self.producer_running = False
            self.consumer_running = False
            
            self.add_log("模拟已暂停")
            
            # 更新状态显示
            self.update_status_display()
        else:
            # 启动
            self.simulation_running = True
            self.producer_timer.start(self.produce_interval)
            self.consumer_timer.start(self.consume_interval)
            
            # 更新生产者和消费者状态为运行中
            self.producer_running = True
            self.consumer_running = True
            
            self.add_log("模拟已启动")
            
            # 更新状态显示
            self.update_status_display()
    
    def reset_simulation(self):
        """重置模拟"""
        # 停止所有定时器
        self.simulation_running = False
        self.producer_timer.stop()
        self.consumer_timer.stop()
        self.animation_timer.stop()
        
        # 重置状态
        self.message_queue.clear()
        self.producer_running = False
        self.consumer_running = False
        self.producer_blocked = False
        self.consumer_blocked = False
        self.message_id = 1
        
        # 清除所有消息项
        for message_item, message_text in self.message_items:
            self.graphics_view.scene().removeItem(message_item)
            self.graphics_view.scene().removeItem(message_text)
        self.message_items.clear()
        
        # 清除动画
        self.animations.clear()
        self.is_animating = False
        
        # 重置UI - 已移除start_button，无需重置
        
        # 更新状态显示
        self.update_status_display()
        
        # 日志组件已删除，不再清除日志
        
    def produce_message(self):
        """生产者生成消息"""
        if len(self.message_queue) < self.max_queue_size:
            # 队列未满，生成消息
            message = f"消息 {self.message_id}"
            self.message_queue.append(message)
            self.message_id += 1
            
            # 更新可视化
            self.update_visualization(self.message_queue)
            
            # 记录日志
            self.add_log(f"生产者生成: {message} 队列大小: {len(self.message_queue)}")
            
            # 更新状态
            self.producer_running = True
            self.producer_blocked = False
            
            # 启动呼吸灯
            self.producer_breathing = True
            
        else:
            # 队列已满，生产者阻塞
            self.producer_running = False
            self.producer_blocked = True
            self.add_log(f"队列已满 ({len(self.message_queue)}/{self.max_queue_size})，生产者阻塞")
            
            # 启动队列警告动画
            self.queue_warning = True
        
        # 更新状态显示
        self.update_status_display()
        
    def consume_message(self):
        """消费者消费消息"""
        if self.message_queue:
            # 队列有消息，消费消息
            message = self.message_queue.pop(0)
            
            # 更新可视化
            self.update_visualization(self.message_queue)
            
            # 记录日志
            self.add_log(f"消费者接收: {message} 队列大小: {len(self.message_queue)}")
            
            # 更新状态
            self.consumer_running = True
            self.consumer_blocked = False
            
            # 启动呼吸灯
            self.consumer_breathing = True
            
            # 如果生产者之前阻塞，现在检查是否可以恢复
            if self.producer_blocked and len(self.message_queue) < self.max_queue_size:
                self.producer_blocked = False
                self.producer_running = True
                self.add_log(f"队列有空闲 ({len(self.message_queue)}/{self.max_queue_size})，生产者恢复")
                
                # 停止队列警告
                self.queue_warning = False
        else:
            # 队列为空，消费者阻塞
            self.consumer_running = False
            self.consumer_blocked = True
            self.add_log("队列为空，消费者阻塞")
        
        # 更新状态显示
        self.update_status_display()
    
    def update_produce_interval(self, value):
        """更新生产间隔"""
        self.produce_interval = value
        if self.simulation_running:
            self.producer_timer.setInterval(value)
        self.add_log(f"生产间隔更新为 {value} ms")
    
    def update_consume_interval(self, value):
        """更新消费间隔"""
        self.consume_interval = value
        if self.simulation_running:
            self.consumer_timer.setInterval(value)
        self.add_log(f"消费间隔更新为 {value} ms")
    
    def update_queue_size(self, value):
        """更新队列大小"""
        self.max_queue_size = value
        self.add_log(f"队列容量更新为 {value} 条")
        
        # 重新初始化场景以更新队列槽位
        self.init_scene()
    
    def update_status_display(self):
        """更新状态显示"""
        
        # 更新生产者状态
        if self.producer_blocked:
            self.producer_status_label.setText(f"生产者: 阻塞")
            self.producer_status_label.setStyleSheet("color: #ef4444; padding: 8px 15px; border-radius: 20px; background-color: #fee2e2;")
        elif self.producer_running:
            self.producer_status_label.setText(f"生产者: 运行中")
            self.producer_status_label.setStyleSheet("color: #16a34a; padding: 8px 15px; border-radius: 20px; background-color: #dcfce7;")
        else:
            self.producer_status_label.setText(f"生产者: 已停止")
            self.producer_status_label.setStyleSheet("color: #6b7280; padding: 8px 15px; border-radius: 20px; background-color: #f3f4f6;")
        
        # 更新队列状态
        queue_size = len(self.message_queue)
        if queue_size == self.max_queue_size:
            self.queue_status_label.setText(f"消息队列: {queue_size}/{self.max_queue_size} (已满)")
            self.queue_status_label.setStyleSheet("color: #ef4444; padding: 8px 15px; border-radius: 20px; background-color: #fee2e2;")
        elif queue_size == 0:
            self.queue_status_label.setText(f"消息队列: {queue_size}/{self.max_queue_size} (空)")
            self.queue_status_label.setStyleSheet("color: #6b7280; padding: 8px 15px; border-radius: 20px; background-color: #f3f4f6;")
        else:
            self.queue_status_label.setText(f"消息队列: {queue_size}/{self.max_queue_size}")
            self.queue_status_label.setStyleSheet("color: #f59e0b; padding: 8px 15px; border-radius: 20px; background-color: #fef3c7;")
        
        # 更新消费者状态
        if self.consumer_blocked:
            self.consumer_status_label.setText(f"消费者: 阻塞")
            self.consumer_status_label.setStyleSheet("color: #ef4444; padding: 8px 15px; border-radius: 20px; background-color: #fee2e2;")
        elif self.consumer_running:
            self.consumer_status_label.setText(f"消费者: 运行中")
            self.consumer_status_label.setStyleSheet("color: #3b82f6; padding: 8px 15px; border-radius: 20px; background-color: #dbeafe;")
        else:
            self.consumer_status_label.setText(f"消费者: 已停止")
            self.consumer_status_label.setStyleSheet("color: #6b7280; padding: 8px 15px; border-radius: 20px; background-color: #f3f4f6;")
        
        # 更新全局状态
        with STATUS._lock:
            STATUS.message_queue = self.message_queue
    
    def draw_background(self):
        """绘制背景装饰"""
        # 渐变背景 - 更新宽度以匹配场景
        background_rect = QRectF(0, 0, 1200, 400)
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0, QColor(249, 250, 251))
        gradient.setColorAt(1, QColor(243, 244, 246))
        background = QGraphicsRectItem(background_rect)
        background.setBrush(QBrush(gradient))
        background.setPen(QPen(QColor(226, 232, 240), 1))
        self.scene.addItem(background)
        
        # 移除装饰线
        # line = QGraphicsRectItem(0, 180, 1200, 1)
        # line.setBrush(QBrush(QColor(226, 232, 240), Qt.BrushStyle.SolidPattern))
        # self.scene.addItem(line)
    
    def draw_queue_area(self):
        """绘制消息队列区域"""
        # 队列标题 - 在生产者和消费者之间居中显示
        queue_title = QGraphicsTextItem("消息队列")
        queue_title.setDefaultTextColor(QColor(100, 100, 100))
        queue_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        # 计算文本宽度并在生产者和消费者之间居中显示
        title_width = queue_title.boundingRect().width()
        center_x = (305 + 875) / 2 -50 # 生产者和消费者的水平中心位置
        queue_title.setPos(center_x - title_width / 2, 50)  # 高度保持不变
        self.scene.addItem(queue_title)
        
        # 队列容量文本 - 居中显示在标题右侧
        capacity_text = QGraphicsTextItem(f"容量: {self.max_queue_size}")
        capacity_text.setDefaultTextColor(QColor(156, 163, 175))
        capacity_text.setFont(QFont("Segoe UI", 12))
        capacity_text.setPos(center_x + title_width / 2 + 10, 55)  # 标题右侧10像素，高度保持不变
        self.scene.addItem(capacity_text)
        
        # 绘制队列槽位
        for i in range(self.max_queue_size):
            slot_pos = self.queue_start_pos + QPointF(i * self.queue_spacing, 0)
            
            # 槽位背景
            slot_rect = QRectF(0, 0, 50, 50)
            slot_item = QGraphicsRectItem(slot_rect)
            slot_item.setBrush(QBrush(QColor(243, 244, 246), Qt.BrushStyle.SolidPattern))  # 浅灰色
            slot_item.setPen(QPen(QColor(226, 232, 240), 2))  # 灰色边框
            slot_item.setPos(slot_pos - QPointF(25, 25))
            self.scene.addItem(slot_item)
            
            # 槽位编号
            slot_number = QGraphicsTextItem(str(i + 1))
            slot_number.setDefaultTextColor(QColor(156, 163, 175))
            slot_number.setFont(QFont("Segoe UI", 9))
            slot_number.setPos(slot_pos + QPointF(15, 15))
            self.scene.addItem(slot_number)
    
    def draw_arrows(self):
        """绘制生产者到队列和队列到消费者的箭头"""
        # 生产者到队列的箭头
        self.draw_arrow(self.producer_pos + QPointF(50, 0), self.queue_start_pos - QPointF(50, 0), QColor(34, 197, 94))
        
        # 队列到消费者的箭头
        queue_end_pos = self.queue_start_pos + QPointF((self.max_queue_size - 1) * self.queue_spacing, 0)
        self.draw_arrow(queue_end_pos + QPointF(50, 0), self.consumer_pos - QPointF(50, 0), QColor(59, 130, 246))
    
    def draw_arrow(self, start_pos, end_pos, color):
        """绘制带箭头的线段"""
        # 计算线段方向
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        length = (dx ** 2 + dy ** 2) ** 0.5
        
        # 绘制主线段
        line_item = QGraphicsRectItem(0, 0, length, 3)
        line_item.setBrush(QBrush(color, Qt.BrushStyle.SolidPattern))
        line_item.setPos(start_pos)
        line_item.setRotation(90 if length == 0 else (dy / length) * 180 / 3.14159)
        self.scene.addItem(line_item)
        
        # 绘制箭头
        arrow_size = 15
        arrow_angle = 30
        
        # 计算箭头点
        arrow_point1 = QPointF(end_pos.x() - arrow_size * (dx * 3.14159 / 180 * arrow_angle + dy * 3.14159 / 180 * arrow_angle), 
                              end_pos.y() - arrow_size * (dy * 3.14159 / 180 * arrow_angle - dx * 3.14159 / 180 * arrow_angle))
        arrow_point2 = QPointF(end_pos.x() - arrow_size * (dx * 3.14159 / 180 * arrow_angle - dy * 3.14159 / 180 * arrow_angle), 
                              end_pos.y() - arrow_size * (dy * 3.14159 / 180 * arrow_angle + dx * 3.14159 / 180 * arrow_angle))
        
        # 绘制箭头线段
        arrow_line1 = QGraphicsLineItem(end_pos.x(), end_pos.y(), arrow_point1.x(), arrow_point1.y())
        arrow_line1.setPen(QPen(color, 3))
        self.scene.addItem(arrow_line1)
        
        arrow_line2 = QGraphicsLineItem(end_pos.x(), end_pos.y(), arrow_point2.x(), arrow_point2.y())
        arrow_line2.setPen(QPen(color, 3))
        self.scene.addItem(arrow_line2)
    
    def add_log(self, message):
        """添加日志信息到控制台"""
        # 由于日志组件已删除，现在只打印到控制台
        current_time = QDateTime.currentDateTime().toString("HH:mm:ss")
        log_entry = f"[{current_time}] {message}"
        print(log_entry)
    
    def animate_produce(self, message, index):
        """动画展示消息产生过程"""
        scene = self.graphics_view.scene()
        
        # 创建新的消息项（待发送状态：浅绿）
        message_item = QGraphicsRectItem(0, 0, 50, 40)
        message_item.setBrush(QBrush(QColor(240, 253, 244)))
        message_item.setPen(QPen(QColor(34, 197, 94), 2))
        message_item.setPos(self.producer_pos - QPointF(25, 20))
        message_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        scene.addItem(message_item)
        
        # 添加消息文本
        message_text = QGraphicsTextItem(message)
        message_text.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        message_text.setPos(self.producer_pos - QPointF(20, 10))
        message_text.setDefaultTextColor(QColor(34, 197, 94))
        scene.addItem(message_text)
        
        # 存储消息项
        self.message_items.append((message_item, message_text))
        
        # 移动到队列位置的动画
        target_pos = self.queue_start_pos + QPointF(index * self.queue_spacing, 0)
        
        # 记录动画信息
        start_time = QTime.currentTime().msecsSinceStartOfDay()
        duration = 500  # 动画持续时间
        
        # 消息项动画
        self.animations.append({
            'item': message_item,
            'start_pos': self.producer_pos - QPointF(25, 20),
            'end_pos': target_pos - QPointF(25, 20),
            'start_time': start_time,
            'duration': duration
        })
        
        # 文本动画
        self.animations.append({
            'item': message_text,
            'start_pos': self.producer_pos - QPointF(20, 10),
            'end_pos': target_pos - QPointF(20, 10),
            'start_time': start_time,
            'duration': duration
        })
        
        # 启动动画定时器
        if not self.is_animating:
            self.is_animating = True
            self.animation_timer.start()
    
    def animate_consume(self, remaining_size):
        """动画展示消息消费过程"""
        if not self.message_items:
            return
            
        # 获取第一个消息项（要被消费的）
        message_item, message_text = self.message_items[0]
        
        # 移动到消费者的动画
        start_pos_item = message_item.pos()
        start_pos_text = message_text.pos()
        end_pos_item = self.consumer_pos - QPointF(25, 20)
        end_pos_text = self.consumer_pos - QPointF(20, 10)
        
        # 记录动画信息
        start_time = QTime.currentTime().msecsSinceStartOfDay()
        duration = 500  # 动画持续时间
        
        # 标记这是消费动画，需要在完成后移除
        consume_animation = {
            'item': message_item,
            'start_pos': start_pos_item,
            'end_pos': end_pos_item,
            'start_time': start_time,
            'duration': duration,
            'is_consume': True,
            'text_item': message_text
        }
        
        # 消息项动画
        self.animations.append(consume_animation)
        
        # 文本动画
        self.animations.append({
            'item': message_text,
            'start_pos': start_pos_text,
            'end_pos': end_pos_text,
            'start_time': start_time,
            'duration': duration
        })
        
        # 启动动画定时器
        if not self.is_animating:
            self.is_animating = True
            self.animation_timer.start()
    
    def update_message_positions(self):
        """更新剩余消息项的位置"""
        for i, (message_item, message_text) in enumerate(self.message_items):
            target_pos = self.queue_start_pos + QPointF(i * self.queue_spacing, 0)
            
            # 记录动画信息
            start_time = QTime.currentTime().msecsSinceStartOfDay()
            duration = 400  # 动画持续时间
            
            # 消息项动画
            self.animations.append({
                'item': message_item,
                'start_pos': message_item.pos(),
                'end_pos': target_pos - QPointF(25, 20),
                'start_time': start_time,
                'duration': duration
            })
            
            # 文本动画
            self.animations.append({
                'item': message_text,
                'start_pos': message_text.pos(),
                'end_pos': target_pos - QPointF(20, 10),
                'start_time': start_time,
                'duration': duration
            })
            
            # 启动动画定时器
            if not self.is_animating:
                self.is_animating = True
                self.animation_timer.start()
    
    def update_animations(self):
        """更新所有正在进行的动画"""
        current_time = QTime.currentTime().msecsSinceStartOfDay()
        animations_to_remove = []
        
        for i, anim in enumerate(self.animations):
            elapsed = current_time - anim['start_time']
            
            if elapsed >= anim['duration']:
                # 动画完成
                anim['item'].setPos(anim['end_pos'])
                animations_to_remove.append(i)
                
                # 如果是消费动画，移除消息项
                if 'is_consume' in anim and anim['is_consume']:
                    self.graphics_view.scene().removeItem(anim['item'])
                    self.graphics_view.scene().removeItem(anim['text_item'])
                    self.message_items.pop(0)
                    
                    # 更新剩余消息项的位置
                    self.update_message_positions()
                else:
                    # 进入队列后改变颜色（排队中状态：浅黄）
                    if hasattr(anim['item'], 'setBrush'):
                        anim['item'].setBrush(QBrush(QColor(254, 252, 232)))
                        anim['item'].setPen(QPen(QColor(245, 158, 11), 2))
                    # 对于文本项，更新文本颜色
                    if hasattr(anim['item'], 'setDefaultTextColor'):
                        anim['item'].setDefaultTextColor(QColor(245, 158, 11))
            else:
                # 计算当前位置（使用缓动函数）
                progress = elapsed / anim['duration']
                # 缓动函数：easeOutBounce（弹跳效果）
                if progress < 1 / 2.75:
                    current_progress = 7.5625 * progress * progress
                elif progress < 2 / 2.75:
                    progress -= 1.5 / 2.75
                    current_progress = 7.5625 * progress * progress + 0.75
                elif progress < 2.5 / 2.75:
                    progress -= 2.25 / 2.75
                    current_progress = 7.5625 * progress * progress + 0.9375
                else:
                    progress -= 2.625 / 2.75
                    current_progress = 7.5625 * progress * progress + 0.984375
                
                current_pos = QPointF(
                    anim['start_pos'].x() + (anim['end_pos'].x() - anim['start_pos'].x()) * current_progress,
                    anim['start_pos'].y() + (anim['end_pos'].y() - anim['start_pos'].y()) * current_progress
                )
                
                # 更新位置
                anim['item'].setPos(current_pos)
        
        # 移除已完成的动画
        for i in reversed(animations_to_remove):
            del self.animations[i]
        
        # 更新呼吸灯效果
        self.update_breathing_effect()
        
        # 如果没有动画了，停止定时器
        if not self.animations:
            self.is_animating = False
            self.animation_timer.stop()
    
    def update_breathing_effect(self):
        """更新呼吸灯效果"""
        # 获取当前时间，避免变量未定义
        current_time = QTime.currentTime().msecsSinceStartOfDay() % 1500
        
        if self.producer_breathing:
            # 生产者呼吸灯效果
            if current_time < 750:
                opacity = 0.8 + (current_time / 750) * 0.2
            else:
                opacity = 1.0 - ((current_time - 750) / 750) * 0.2
            
            producer_gradient = QLinearGradient(0, 0, 80, 60)
            producer_gradient.setColorAt(0, QColor(74, 222, 128, int(opacity * 255)))
            producer_gradient.setColorAt(1, QColor(34, 197, 94, int(opacity * 255)))
            self.producer_item.setBrush(QBrush(producer_gradient))
        
        if self.consumer_breathing:
            # 消费者呼吸灯效果
            if current_time < 750:
                opacity = 0.8 + (current_time / 750) * 0.2
            else:
                opacity = 1.0 - ((current_time - 750) / 750) * 0.2
            
            consumer_gradient = QLinearGradient(0, 0, 80, 60)
            consumer_gradient.setColorAt(0, QColor(56, 189, 248, int(opacity * 255)))
            consumer_gradient.setColorAt(1, QColor(14, 165, 233, int(opacity * 255)))
            self.consumer_item.setBrush(QBrush(consumer_gradient))
        
        # 重置呼吸灯
        if current_time > 1400:
            self.producer_breathing = False
            self.consumer_breathing = False
    
    def clear_all(self):
        """清除所有消息项和动画"""
        # 停止所有定时器
        self.animation_timer.stop()
        self.breathing_timer.stop()
        self.is_animating = False
        
        # 清除所有消息项
        for message_item, message_text in self.message_items:
            self.graphics_view.scene().removeItem(message_item)
            self.graphics_view.scene().removeItem(message_text)
        
        self.message_items.clear()
        self.animations.clear()
        self.last_queue_size = 0


# === 新增类：共享内存可视化组件 ===
class QtSharedMemoryVisualization(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.simulation_running = False
        
        # 主布局 - 垂直布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        
        # 内容布局 - 水平布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 左侧写入日志面板
        self.write_log = QTextEdit()
        self.write_log.setReadOnly(True)
        self.write_log.setStyleSheet("background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; font-family: Consolas, monospace;")
        self.write_log.setMinimumWidth(200)
        self.write_log.append("写入日志开始...")
        
        # 中间图形视图
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setStyleSheet("border: 2px solid #cbd5e1; border-radius: 8px; background-color: #f8fafc;")
        self.view.setMinimumSize(700, 400)
        
        # 右侧读取日志面板
        self.read_log = QTextEdit()
        self.read_log.setReadOnly(True)
        self.read_log.setStyleSheet("background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; font-family: Consolas, monospace;")
        self.read_log.setMinimumWidth(200)
        self.read_log.append("读取日志开始...")
        
        # 添加组件到内容布局
        content_layout.addWidget(self.write_log)
        content_layout.addWidget(self.view)
        content_layout.addWidget(self.read_log)
        
        # 将内容布局添加到主布局
        main_layout.addLayout(content_layout)
        
        # 添加重置按钮
        self.reset_button = QPushButton("重置模拟")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        self.reset_button.clicked.connect(self.reset_simulation)
        
        # 将按钮居中添加到主布局
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.reset_button, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(button_layout)
        
        # 内存块图形项列表
        self.memory_blocks = [] # 存储 (RectItem, TextItem) 元组
        
        self.init_scene()
        
        # 动画定时器 (用于刷新可视化)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_visualization)
        self.timer.start(50) # 20 FPS
        
        # 操作定时器 (用于控制读写操作频率)
        self.operation_timer = QTimer()
        self.operation_timer.timeout.connect(self.perform_operation)
        self.operation_interval = 500  # 每500ms执行一次操作
        self.operation_timer.start(self.operation_interval)

    def init_scene(self):
        self.scene.clear()
        self.scene.setSceneRect(0, 0, 700, 350)
        
        # 1. 绘制 Writer 区域 (左侧)
        self.draw_process_area(50, 100, "Writer Processes", QColor(254, 202, 202), "写入数据")
        
        # 2. 绘制 Reader 区域 (右侧)
        self.draw_process_area(550, 100, "Reader Processes", QColor(191, 219, 254), "读取数据")
        
        # 3. 绘制共享内存区域 (中间)
        # 4x4 网格
        start_x = 220
        start_y = 50
        block_size = 60
        gap = 10
        
        # 背景底板
        bg = QGraphicsRectItem(start_x - 20, start_y - 20, (block_size+gap)*4 + 30, (block_size+gap)*4 + 30)
        bg.setBrush(QBrush(QColor(241, 245, 249)))
        bg.setPen(QPen(QColor(148, 163, 184), 2, Qt.PenStyle.DashLine))
        self.scene.addItem(bg)
        
        title = QGraphicsTextItem("Shared Memory Segment")
        title.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        title.setPos(start_x + 40, start_y - 50)
        self.scene.addItem(title)

        self.memory_blocks = []
        
        for i in range(16):
            row = i // 4
            col = i % 4
            x = start_x + col * (block_size + gap)
            y = start_y + row * (block_size + gap)
            
            # 内存块矩形
            rect = QGraphicsRectItem(0, 0, block_size, block_size)
            rect.setPos(x, y)
            rect.setBrush(QBrush(QColor("white")))
            rect.setPen(QPen(QColor("#94a3b8"), 2))
            self.scene.addItem(rect)
            
            # 地址标签 (左上角小字)
            addr_text = QGraphicsTextItem(f"0x{i:X}")
            addr_text.setFont(QFont("Arial", 8))
            addr_text.setDefaultTextColor(QColor("gray"))
            addr_text.setPos(x + 2, y + 2)
            self.scene.addItem(addr_text)
            
            # 数据内容 (中间大字)
            data_text = QGraphicsTextItem("00")
            data_text.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
            data_text.setPos(x + 10, y + 15)
            self.scene.addItem(data_text)
            
            self.memory_blocks.append((rect, data_text))

    def draw_process_area(self, x, y, title, color, desc):
        """绘制左右两侧的进程示意图"""
        # 圆形代表进程集合
        circle = QGraphicsRectItem(x, y, 100, 100) 
        circle.setBrush(QBrush(color))
        circle.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(circle)
        
        text = QGraphicsTextItem(title)
        text.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text.setPos(x + 5, y + 110)
        self.scene.addItem(text)
        
        desc_item = QGraphicsTextItem(desc)
        desc_item.setFont(QFont("Arial", 9))
        desc_item.setDefaultTextColor(QColor("gray"))
        desc_item.setPos(x + 20, y + 40)
        self.scene.addItem(desc_item)

    def toggle_simulation(self):
        self.simulation_running = not self.simulation_running
        if self.simulation_running:
            print("共享内存模拟已启动")
            # 初始化共享内存数据
            import random
            with STATUS._lock:
                STATUS.shm_data = ['00'] * 16
        else:
            print("共享内存模拟已停止")
        
    def reset_simulation(self):
        self.simulation_running = False
        with STATUS._lock:
            # 重置共享内存数据
            STATUS.shm_data = ['00'] * 16
            # 清除操作历史
            STATUS.shm_ops.clear()
            # 清除旧的单操作记录（向后兼容）
            if hasattr(STATUS, 'shm_last_op'):
                STATUS.shm_last_op = None
        
        # 清除日志
        self.write_log.clear()
        self.write_log.append("写入日志开始...")
        self.read_log.clear()
        self.read_log.append("读取日志开始...")
        
        # 重新初始化场景
        self.init_scene()
    
    def perform_operation(self):
        """每隔一段时间执行一次读写操作"""
        import random
        import time
        
        # 如果模拟正在运行，随机执行读写操作
        if self.simulation_running:
            with STATUS._lock:
                # 确保shm_data存在
                if not hasattr(STATUS, 'shm_data'):
                    STATUS.shm_data = ['00'] * 16
                
                # 随机选择写或读操作
                op_type = random.choice(['WRITE', 'READ'])
                addr = random.randint(0, 15)
                
                if op_type == 'WRITE':
                    # 随机生成两个字符作为数据
                    new_data = random.choice(['01', '02', '03', '04', '05', '06', '07', '08', '09', '10'])
                    STATUS.shm_data[addr] = new_data
                    # 将操作追加到操作列表
                    STATUS.shm_ops.append({
                        'type': 'WRITE',
                        'addr': addr,
                        'val': new_data,
                        'time': time.time()
                    })
                    # 保持操作列表不超过20个元素
                    if len(STATUS.shm_ops) > 20:
                        STATUS.shm_ops.pop(0)
                    # 记录写入日志
                    timestamp = time.strftime('%H:%M:%S')
                    log_msg = f"[{timestamp}] 写入地址0x{addr:X}: {new_data}\n"
                    self.write_log.insertPlainText(log_msg)
                    self.write_log.moveCursor(QTextCursor.MoveOperation.End)
                else:
                    # 将操作追加到操作列表
                    STATUS.shm_ops.append({
                        'type': 'READ',
                        'addr': addr,
                        'val': STATUS.shm_data[addr],
                        'time': time.time()
                    })
                    # 保持操作列表不超过20个元素
                    if len(STATUS.shm_ops) > 20:
                        STATUS.shm_ops.pop(0)
                    # 记录读取日志
                    timestamp = time.strftime('%H:%M:%S')
                    data = STATUS.shm_data[addr]
                    log_msg = f"[{timestamp}] 读取地址0x{addr:X}: {data}\n"
                    self.read_log.insertPlainText(log_msg)
                    self.read_log.moveCursor(QTextCursor.MoveOperation.End)

    def update_visualization(self):
        """每帧刷新，更新可视化显示"""
        import time
        
        # 更新可视化显示
        if hasattr(STATUS, 'shm_data') and STATUS.shm_data:
            with STATUS._lock:
                # 1. 更新所有内存块的文本内容
                for i, val in enumerate(STATUS.shm_data):
                    if i < len(self.memory_blocks):
                        self.memory_blocks[i][1].setPlainText(str(val))
                
                # 2. 获取最近的操作列表
                recent_ops = STATUS.shm_ops.copy()
                
            current_time = time.time()
            # 记录需要高亮的内存块及其操作类型
            highlight_ops = {}

            # 遍历所有最近操作，找出0.5秒内的操作
            for op in recent_ops:
                time_diff = current_time - op.get('time', 0)
                if time_diff < 0.5:
                    addr = op.get('addr', -1)
                    # 如果同一个地址有多个操作，只保留最新的
                    if addr not in highlight_ops or op.get('time', 0) > highlight_ops[addr].get('time', 0):
                        highlight_ops[addr] = op

            # 先重置所有内存块的颜色
            for i, (rect, _) in enumerate(self.memory_blocks):
                rect.setBrush(QBrush(QColor("white")))
                rect.setPen(QPen(QColor("#94a3b8"), 2))

            # 高亮有操作的内存块
            for addr, op in highlight_ops.items():
                if 0 <= addr < len(self.memory_blocks):
                    rect, _ = self.memory_blocks[addr]
                    op_type = op.get('type')
                    
                    if op_type == 'WRITE':
                        # 写操作：红色高亮
                        rect.setBrush(QBrush(QColor(252, 165, 165)))
                        rect.setPen(QPen(QColor(220, 38, 38), 3))
                    elif op_type == 'READ':
                        # 读操作：蓝色高亮
                        rect.setBrush(QBrush(QColor(147, 197, 253)))
                        rect.setPen(QPen(QColor(37, 99, 235), 3))