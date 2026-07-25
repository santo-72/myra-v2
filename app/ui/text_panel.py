from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt

class TextPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFrameStyle(0)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #00FFFF;
                padding: 5px;
            }
        """)
        
        font = QFont("Consolas", 10)
        self.text_edit.setFont(font)
        
        layout.addWidget(self.text_edit)
        
    def append_text(self, text: str, color: str = "#00FFFF"):
        self.text_edit.append(f"<span style='color: {color};'>{text}</span>")
        
    def clear(self):
        self.text_edit.clear()
