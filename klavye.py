import sys
import threading
import ctypes
import random
import time
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtMultimedia import QMediaPlayer
import keyboard  # pip install keyboard

VK_CAPITAL = 0x14
VK_NUMLOCK = 0x90
VK_SCROLL = 0x91

class Bullet:
    def __init__(self, x, y, dx, dy, color):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.color = color
        self.radius = 7

    def move(self):
        self.x += self.dx
        self.y += self.dy

class SnakeLight(QtWidgets.QWidget):
    def __init__(self, selected_keys_func, get_light_speed_func, get_snake_speed_func, get_color_speed_func, stop_callback):
        super().__init__()
        self.selected_keys_func = selected_keys_func
        self.get_light_speed_func = get_light_speed_func
        self.get_snake_speed_func = get_snake_speed_func
        self.get_color_speed_func = get_color_speed_func
        self.stop_callback = stop_callback

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | 
                            QtCore.Qt.WindowStaysOnTopHint | 
                            QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setWindowFlag(QtCore.Qt.WindowTransparentForInput, True)

        screen_geom = QtWidgets.QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, screen_geom.width(), screen_geom.height())

        self.snake_timer = QtCore.QTimer()
        self.snake_timer.timeout.connect(self.update_snake)
        self.snake_timer.start(30)

        self.bullet_timer = QtCore.QTimer()
        self.bullet_timer.timeout.connect(self.update_bullets)
        self.bullet_timer.start(30)

        self.snake = []
        self.snake_length = 100
        self.x, self.y = 100, 100
        self.dx, self.dy = 0, 0
        self.color_hue = 0

        self.player = QMediaPlayer()

        self.lights_running = True
        self.lights_thread = threading.Thread(target=self.keyboard_lights, daemon=True)
        self.lights_thread.start()

        self.bullets = []

        self.last_mouse_pos = QtGui.QCursor.pos()
        self.mouse_stationary_time = 0
        self.last_time_check = time.time()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.stop_animation()

    def shoot_bullet(self):
        if not self.snake:
            return
        head_x, head_y, _ = self.snake[-1]

        dx, dy = self.dx, self.dy
        length = (dx**2 + dy**2)**0.5
        if length == 0:
            dx, dy = 1, 0
        else:
            dx /= length
            dy /= length

        speed = 15
        bullet_dx = dx * speed
        bullet_dy = dy * speed

        color = QtGui.QColor()
        color.setHsv(int(self.color_hue), 255, 255)
        bullet = Bullet(head_x, head_y, bullet_dx, bullet_dy, color)
        self.bullets.append(bullet)

    def update_bullets(self):
        screen_rect = self.rect()
        to_remove = []
        for b in self.bullets:
            b.move()
            if not screen_rect.contains(int(b.x), int(b.y)):
                to_remove.append(b)
        for b in to_remove:
            self.bullets.remove(b)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        for px, py, color in self.snake:
            painter.setPen(QtGui.QPen(color, 10))
            painter.drawPoint(int(px), int(py))
        for b in self.bullets:
            painter.setBrush(b.color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(int(b.x - b.radius), int(b.y - b.radius), b.radius*2, b.radius*2)

    def update_snake(self):
        snake_speed = self.get_snake_speed_func()
        color_speed = self.get_color_speed_func()

        current_mouse_pos = QtGui.QCursor.pos()
        now = time.time()

        dist = ((current_mouse_pos.x() - self.last_mouse_pos.x())**2 + (current_mouse_pos.y() - self.last_mouse_pos.y())**2)**0.5
        elapsed = now - self.last_time_check

        if dist < 1:
            self.mouse_stationary_time += elapsed
        else:
            self.mouse_stationary_time = 0

        self.last_time_check = now
        self.last_mouse_pos = current_mouse_pos

        if self.mouse_stationary_time > 2:
            if self.dx == 0 and self.dy == 0 or random.random() < 0.05:
                self.dx = random.choice([-1, 1]) * random.uniform(2, 5)
                self.dy = random.choice([-1, 1]) * random.uniform(2, 5)
        else:
            target_x = current_mouse_pos.x()
            target_y = current_mouse_pos.y()
            diff_x = target_x - self.x
            diff_y = target_y - self.y
            distance = (diff_x**2 + diff_y**2)**0.5
            if distance != 0:
                self.dx = (diff_x / distance) * 7 * snake_speed
                self.dy = (diff_y / distance) * 7 * snake_speed

        self.color_hue = (self.color_hue + color_speed) % 360
        color = QtGui.QColor()
        color.setHsv(int(self.color_hue), 255, 255)

        self.snake.append((self.x, self.y, color))
        if len(self.snake) > self.snake_length:
            self.snake.pop(0)

        self.x += self.dx
        self.y += self.dy

        w, h = self.width(), self.height()
        if self.x < 0:
            self.x = 0
            self.dx *= -1
        elif self.x > w:
            self.x = w
            self.dx *= -1

        if self.y < 0:
            self.y = 0
            self.dy *= -1
        elif self.y > h:
            self.y = h
            self.dy *= -1

        self.update()

    def keyboard_lights(self):
        while self.lights_running:
            keys = self.selected_keys_func()
            light_speed = self.get_light_speed_func()
            for key in keys:
                if not self.lights_running:
                    return
                ctypes.windll.user32.keybd_event(key, 0, 0, 0)
                ctypes.windll.user32.keybd_event(key, 0, 2, 0)
                QtCore.QThread.msleep(int(light_speed * 1000))

    def stop_animation(self):
        self.lights_running = False
        self.snake_timer.stop()
        self.bullet_timer.stop()
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.stop()
        self.stop_callback()
        self.close()

class ControlPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kontrol Paneli")
        self.setGeometry(100, 100, 300, 480)

        layout = QtWidgets.QVBoxLayout()

        self.caps_checkbox = QtWidgets.QCheckBox("Caps Lock ")
        self.num_checkbox = QtWidgets.QCheckBox("Num Lock ")
        self.scroll_checkbox = QtWidgets.QCheckBox("Scroll Lock")

        layout.addWidget(self.caps_checkbox)
        layout.addWidget(self.num_checkbox)
        layout.addWidget(self.scroll_checkbox)

        self.light_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.light_speed_slider.setMinimum(1)
        self.light_speed_slider.setMaximum(20)
        self.light_speed_slider.setValue(5)
        layout.addWidget(QtWidgets.QLabel("Klavye Işık Hızı"))
        layout.addWidget(self.light_speed_slider)

        self.snake_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.snake_speed_slider.setMinimum(1)
        self.snake_speed_slider.setMaximum(20)
        self.snake_speed_slider.setValue(5)
        layout.addWidget(QtWidgets.QLabel("Yılan Hızı"))
        layout.addWidget(self.snake_speed_slider)

        self.color_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.color_speed_slider.setMinimum(1)
        self.color_speed_slider.setMaximum(20)
        self.color_speed_slider.setValue(5)
        layout.addWidget(QtWidgets.QLabel("Renk Değişim Hızı"))
        layout.addWidget(self.color_speed_slider)

        self.start_button = QtWidgets.QPushButton("Başlat 🔥")
        self.start_button.clicked.connect(self.start_snake)
        layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Durdur 🛑")
        self.stop_button.clicked.connect(self.stop_snake)
        layout.addWidget(self.stop_button)

        self.setLayout(layout)

        self.snake_window = None

        keyboard.on_press_key("space", self.space_pressed_global)

    def space_pressed_global(self, e):
        if self.snake_window and self.snake_window.isVisible():
            self.snake_window.shoot_bullet()

    def get_selected_keys(self):
        keys = []
        if self.caps_checkbox.isChecked():
            keys.append(VK_CAPITAL)
        if self.num_checkbox.isChecked():
            keys.append(VK_NUMLOCK)
        if self.scroll_checkbox.isChecked():
            keys.append(VK_SCROLL)
        return keys

    def get_light_speed(self):
        return 0.1 * (21 - self.light_speed_slider.value())

    def get_snake_speed(self):
        return 0.1 * self.snake_speed_slider.value()

    def get_color_speed(self):
        return 0.5 * self.color_speed_slider.value()

    def start_snake(self):
        if self.snake_window is None:
            self.snake_window = SnakeLight(
                self.get_selected_keys, 
                self.get_light_speed, 
                self.get_snake_speed,
                self.get_color_speed,
                self.reset_snake
            )
            self.snake_window.show()

    def stop_snake(self):
        if self.snake_window:
            self.snake_window.stop_animation()

    def reset_snake(self):
        self.snake_window = None

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec_())
