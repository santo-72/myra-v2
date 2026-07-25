from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QFont, QPen
from PyQt6.QtCore import Qt, QTimer, QRectF
import math
import random
from app.core.state_machine import AssistantState

class OrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.state = AssistantState.DORMANT
        self.amplitude = 0.0
        self.base_radius = 80
        
        # Particles
        self.particles = [{"angle": random.uniform(0, math.pi*2), "dist": random.uniform(1.2, 2.5), "speed": random.uniform(-0.02, 0.02)} for _ in range(40)]
        
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)
        
        self.colors = {
            AssistantState.DORMANT: QColor(0, 150, 200, 150),
            AssistantState.AUTHENTICATING: QColor(255, 165, 0, 200),
            AssistantState.ACTIVE_LISTENING: QColor(0, 255, 255, 255),
            AssistantState.ACTIVE_THINKING: QColor(0, 100, 255, 200),
            AssistantState.ACTIVE_SPEAKING: QColor(0, 255, 255, 255)
        }

    def set_state(self, state: AssistantState):
        self.state = state
        self.update()
        
    def set_amplitude(self, amp: float):
        self.amplitude = min(1.0, max(0.0, amp))
        self.update()

    def animate(self):
        self.phase += 0.05
        if self.phase > math.pi * 2:
            self.phase = 0
        for p in self.particles:
            p["angle"] += p["speed"]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        pulse = math.sin(self.phase) * 5
        active_radius = self.base_radius + pulse
        
        if self.state in [AssistantState.ACTIVE_LISTENING, AssistantState.ACTIVE_SPEAKING]:
            active_radius += self.amplitude * 30
            
        color = self.colors.get(self.state, QColor(0, 255, 255))
        
        # Outer faint rings
        painter.setPen(QPen(QColor(0, 255, 255, 50), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(center_x - active_radius*1.8, center_y - active_radius*1.8, active_radius*3.6, active_radius*3.6))
        
        # Inner glow
        gradient = QRadialGradient(center_x, center_y, active_radius * 1.5)
        glow_color = QColor(color)
        glow_color.setAlpha(int(color.alpha() * 0.4))
        gradient.setColorAt(0, glow_color)
        fade_color = QColor(color)
        fade_color.setAlpha(0)
        gradient.setColorAt(1, fade_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QRectF(center_x - active_radius*1.5, center_y - active_radius*1.5, active_radius*3, active_radius*3))
                                   
        # Solid inner ring
        painter.setPen(QPen(color, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(center_x - active_radius, center_y - active_radius, active_radius*2, active_radius*2))
        
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 100), 1))
        painter.drawEllipse(QRectF(center_x - active_radius*0.8, center_y - active_radius*0.8, active_radius*1.6, active_radius*1.6))
        
        # Draw particles
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            px = center_x + math.cos(p["angle"]) * (active_radius * p["dist"])
            py = center_y + math.sin(p["angle"]) * (active_radius * p["dist"])
            psize = 3 + math.sin(self.phase + p["angle"]) * 2
            pcolor = QColor(color)
            pcolor.setAlpha(150)
            painter.setBrush(pcolor)
            painter.drawEllipse(QRectF(px, py, psize, psize))

        # Text "MYRA"
        font = QFont("Arial", 40, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(0, 255, 255, 255))
        painter.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignmentFlag.AlignCenter, "MYRA")
