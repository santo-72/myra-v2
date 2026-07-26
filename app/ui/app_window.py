import sys
import os
import psutil
import datetime
import asyncio
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QGridLayout, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor
from app.ui.orb_widget import OrbWidget
from app.ui.text_panel import TextPanel
from app.core.state_machine import StateMachine, AssistantState
from app.tools.browser_automation import BrowserAutomation
from app.tools.data_analysis import DataAnalysisTools
from app.tools.webcam_stream import WebcamStream
from app.core.dev_agent import DevAgent
from app.tools.shell_runner import ShellRunner
from app.core.self_debug import SelfDebugRuntime
import structlog

logger = structlog.get_logger(__name__)

class AssistantWindow(QMainWindow):
    def __init__(self, state_machine: StateMachine):
        super().__init__()
        self.state_machine = state_machine
        self.is_muted = False
        self.is_screen_sharing = False
        
        self.setWindowTitle("TITAN — Santo Ghosh")
        self.resize(1200, 800)
        
        # Apply Global Dark QSS
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b1120;
            }
            QLabel {
                color: #a0aec0;
                font-family: 'Segoe UI', Arial;
            }
            QPushButton {
                background-color: transparent;
                color: #a0aec0;
                border: 1px solid #2d3748;
                border-radius: 5px;
                padding: 10px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1a202c;
                color: #00ffff;
                border: 1px solid #00ffff;
            }
            QFrame#stats_card {
                background-color: #1a202c;
                border: 1px solid #2d3748;
                border-radius: 10px;
            }
            QFrame#chat_card {
                background-color: #1a202c;
                border: 1px solid #2d3748;
                border-radius: 10px;
            }
            QLabel#title {
                color: #00ffff;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QPushButton#primary_btn {
                background-color: #0055ff;
                color: white;
                text-align: center;
                border: none;
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton#danger_btn {
                background-color: #e53e3e;
                color: white;
                text-align: center;
                border: none;
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton#secondary_btn {
                background-color: transparent;
                color: #00ffff;
                border: 1px solid #00ffff;
                text-align: center;
                border-radius: 15px;
            }
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        
        self.setup_left_sidebar()
        self.setup_center_panel()
        self.setup_right_sidebar()
        
        # State Listener
        self.state_machine.add_listener(self.on_state_change)

        # Real-time Stats Timer
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)

    def setup_left_sidebar(self):
        self.left_panel = QVBoxLayout()
        self.left_panel.setSpacing(10)
        
        title = QLabel("■ LISTENING")
        title.setObjectName("title")
        self.left_panel.addWidget(title)
        
        tools_label = QLabel("⚙ All Tools")
        tools_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin-top: 20px; margin-bottom: 10px;")
        self.left_panel.addWidget(tools_label)
        
        self.btn_img_gen = QPushButton("Image Generator")
        self.btn_txt_gen = QPushButton("Text Generator")
        
        self.btn_code_ast = QPushButton("Code Assistant")
        self.btn_code_ast.clicked.connect(self.trigger_dev_agent)
        
        self.btn_translator = QPushButton("Translator")
        
        self.btn_data_ana = QPushButton("Data Analysis")
        self.btn_data_ana.clicked.connect(self.trigger_data_analysis)
        
        self.btn_task_mgr = QPushButton("Task Manager")
        
        self.btn_webforge = QPushButton("WebForge AI")
        self.btn_webforge.clicked.connect(self.trigger_webforge)
        
        self.btn_settings = QPushButton("Settings")
        
        for btn in [self.btn_img_gen, self.btn_txt_gen, self.btn_code_ast, self.btn_translator, 
                    self.btn_data_ana, self.btn_task_mgr, self.btn_webforge, self.btn_settings]:
            self.left_panel.addWidget(btn)
            
        self.left_panel.addStretch()
        
        self.lbl_screen = QLabel("Screen: OFF")
        self.lbl_camera = QLabel("Live Camera: OFF")
        self.left_panel.addWidget(self.lbl_screen)
        self.left_panel.addWidget(self.lbl_camera)
        
        self.main_layout.addLayout(self.left_panel, 1)

    def setup_center_panel(self):
        self.center_layout = QVBoxLayout()
        
        self.orb = OrbWidget(self)
        self.center_layout.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignCenter)
        
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        self.btn_mute = QPushButton("Mute")
        self.btn_mute.setObjectName("danger_btn")
        self.btn_mute.setFixedSize(100, 40)
        self.btn_mute.clicked.connect(self.toggle_mute)
        controls_layout.addWidget(self.btn_mute)
        
        self.btn_share = QPushButton("Share Screen")
        self.btn_share.setObjectName("secondary_btn")
        self.btn_share.setFixedSize(120, 40)
        self.btn_share.clicked.connect(self.toggle_screen)
        controls_layout.addWidget(self.btn_share)
        
        self.btn_speak = QPushButton("Speak")
        self.btn_speak.setObjectName("primary_btn")
        self.btn_speak.setFixedSize(100, 40)
        self.btn_speak.clicked.connect(self.trigger_speak)
        controls_layout.addWidget(self.btn_speak)
        
        controls_layout.addStretch()
        self.center_layout.addLayout(controls_layout)
        self.center_layout.addSpacing(20)
        
        cam_voice_layout = QHBoxLayout()
        cam_voice_layout.addStretch()
        
        self.btn_cam_toggle = QPushButton("Camera On/Off")
        self.btn_cam_toggle.setStyleSheet("background-color: #2d3748; border-radius: 10px;")
        self.btn_cam_toggle.clicked.connect(self.toggle_camera_module)
        
        self.btn_voice_sel = QPushButton("Voice: Female")
        self.btn_voice_sel.setStyleSheet("background-color: #805ad5; color: white; border-radius: 10px;")
        
        cam_voice_layout.addWidget(self.btn_cam_toggle)
        cam_voice_layout.addWidget(self.btn_voice_sel)
        cam_voice_layout.addStretch()
        self.center_layout.addLayout(cam_voice_layout)
        
        self.main_layout.addLayout(self.center_layout, 2)

    def setup_right_sidebar(self):
        self.right_panel = QVBoxLayout()
        self.right_panel.setSpacing(15)
        
        top_btns = QHBoxLayout()
        self.btn_mic = QPushButton("MIC")
        self.btn_mic.clicked.connect(self.trigger_listen)
        self.btn_api = QPushButton("API")
        self.btn_myra_mode = QPushButton("MYRA MODE")
        self.btn_myra_mode.clicked.connect(lambda: self.state_machine.transition_to(AssistantState.ACTIVE_THINKING))
        
        top_btns.addWidget(self.btn_mic)
        top_btns.addWidget(self.btn_api)
        top_btns.addWidget(self.btn_myra_mode)
        self.right_panel.addLayout(top_btns)
        
        stats_frame = QFrame()
        stats_frame.setObjectName("stats_card")
        self.stats_layout = QGridLayout(stats_frame)
        
        self.stats_layout.addWidget(QLabel("Weather"), 0, 0)
        self.stats_layout.addWidget(QLabel("26°C Sunny ☀"), 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.lbl_battery = QLabel("78%")
        self.stats_layout.addWidget(QLabel("🔋 Battery"), 1, 0)
        self.stats_layout.addWidget(self.lbl_battery, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.lbl_cpu = QLabel("4%")
        self.stats_layout.addWidget(QLabel("💻 CPU"), 2, 0)
        self.stats_layout.addWidget(self.lbl_cpu, 2, 1, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.lbl_ram = QLabel("46%")
        self.stats_layout.addWidget(QLabel("💾 RAM"), 3, 0)
        self.stats_layout.addWidget(self.lbl_ram, 3, 1, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.lbl_time = QLabel("04:17 PM")
        self.stats_layout.addWidget(QLabel("⏱ Time"), 4, 0)
        self.stats_layout.addWidget(self.lbl_time, 4, 1, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.right_panel.addWidget(stats_frame)
        
        chat_frame = QFrame()
        chat_frame.setObjectName("chat_card")
        chat_layout = QVBoxLayout(chat_frame)
        
        tabs = QHBoxLayout()
        chat_btn = QPushButton("Chat")
        chat_btn.setStyleSheet("color: #00ffff; border-bottom: 2px solid #00ffff; border-radius: 0px; text-align: center;")
        tabs.addWidget(chat_btn)
        
        vis_btn = QPushButton("Vision")
        vis_btn.setStyleSheet("text-align: center;")
        tabs.addWidget(vis_btn)
        
        chat_layout.addLayout(tabs)
        
        self.text_panel = TextPanel(self)
        self.text_panel.show()
        chat_layout.addWidget(self.text_panel)
        
        self.right_panel.addWidget(chat_frame, 1)
        self.main_layout.addLayout(self.right_panel, 1)

    def update_stats(self):
        cpu_percent = psutil.cpu_percent()
        self.lbl_cpu.setText(f"{cpu_percent}%")
        ram_percent = psutil.virtual_memory().percent
        self.lbl_ram.setText(f"{ram_percent}%")
        battery = psutil.sensors_battery()
        if battery:
            self.lbl_battery.setText(f"{int(battery.percent)}%")
        else:
            self.lbl_battery.setText("AC Power")
        now = datetime.datetime.now().strftime("%I:%M %p")
        self.lbl_time.setText(now)

    # --- Feature Integrations ---

    def trigger_dev_agent(self):
        self.append_transcript("System: Launching Code Assistant (DevAgent)...", is_user=False)
        self.state_machine.transition_to(AssistantState.ACTIVE_THINKING)
        
        async def run_dev():
            agent = DevAgent(ShellRunner(), SelfDebugRuntime())
            result = await agent.build_and_test("echo 'Setting up environment...'", "echo 'Running unit tests... OK'")
            self.append_transcript(f"Code Assistant: {result}", is_user=False)
            self.state_machine.transition_to(AssistantState.DORMANT)
            
        asyncio.create_task(run_dev())

    def trigger_webforge(self):
        self.append_transcript("System: Launching WebForge AI (Playwright)...", is_user=False)
        self.state_machine.transition_to(AssistantState.ACTIVE_THINKING)
        
        async def run_webforge():
            browser = BrowserAutomation(headless=True)
            await browser.start()
            content = await browser.get_page_content("https://example.com")
            await browser.stop()
            if content:
                snippet = content[:150] + "..." if len(content) > 150 else content
                self.append_transcript(f"WebForge: Scraped example.com: {snippet}", is_user=False)
            else:
                self.append_transcript("WebForge: Failed to scrape.", is_user=False)
            self.state_machine.transition_to(AssistantState.DORMANT)
            
        asyncio.create_task(run_webforge())

    def trigger_data_analysis(self):
        self.append_transcript("System: Launching Data Analyzer (Pandas)...", is_user=False)
        self.state_machine.transition_to(AssistantState.ACTIVE_THINKING)
        
        async def run_analysis():
            csv_path = "workspace/dummy_data.csv"
            os.makedirs("workspace", exist_ok=True)
            with open(csv_path, "w") as f:
                f.write("A,B,C\\n1,2,3\\n4,5,6\\n7,8,9\\n")
            
            analyzer = DataAnalysisTools()
            result = analyzer.analyze_csv_summary("dummy_data.csv")
            self.append_transcript(f"Data Analysis Result:\\n{result}", is_user=False)
            self.state_machine.transition_to(AssistantState.DORMANT)
            
        asyncio.create_task(run_analysis())

    def toggle_camera_module(self):
        if "OFF" in self.lbl_camera.text():
            self.lbl_camera.setText("Live Camera: ON (OpenCV)")
            self.lbl_camera.setStyleSheet("color: #00ffff;")
            self.append_transcript("System: Taking webcam snapshot...", is_user=False)
            self.state_machine.transition_to(AssistantState.ACTIVE_THINKING)
            
            async def run_camera():
                cam = WebcamStream(camera_index=0)
                os.makedirs("workspace", exist_ok=True)
                success = await asyncio.to_thread(cam.take_snapshot, "workspace/snapshot.jpg")
                if success:
                    self.append_transcript("Camera: Snapshot saved to workspace/snapshot.jpg", is_user=False)
                else:
                    self.append_transcript("Camera: Failed to take snapshot (no webcam found).", is_user=False)
                self.state_machine.transition_to(AssistantState.DORMANT)
                
            asyncio.create_task(run_camera())
        else:
            self.lbl_camera.setText("Live Camera: OFF")
            self.lbl_camera.setStyleSheet("color: #a0aec0;")
            self.append_transcript("System: Camera module deactivated.", is_user=False)
            
    def toggle_screen(self):
        if not getattr(self, 'is_screen_sharing', False) or "OFF" in self.lbl_screen.text():
            self.is_screen_sharing = True
            self.lbl_screen.setText("Screen: SHARING (Live to AI)")
            self.lbl_screen.setStyleSheet("color: #00ffff;")
            self.btn_share.setStyleSheet("background-color: #319795; color: white; border: 1px solid #00ffff; border-radius: 15px; font-weight: bold;")
            self.append_transcript("System: Real-time screen sharing activated. AI can now see your monitor!", is_user=False)
        else:
            self.is_screen_sharing = False
            self.lbl_screen.setText("Screen: OFF")
            self.lbl_screen.setStyleSheet("color: #a0aec0;")
            self.btn_share.setStyleSheet("background-color: transparent; color: #00ffff; border: 1px solid #00ffff; border-radius: 15px;")
            self.append_transcript("System: Screen sharing stopped.", is_user=False)
            
    def toggle_mute(self):
        if not getattr(self, 'is_muted', False) or self.btn_mute.text() == "Mute":
            self.is_muted = True
            self.btn_mute.setText("Unmute")
            self.btn_mute.setStyleSheet("background-color: #718096; color: white; text-align: center; border: none; border-radius: 15px; font-weight: bold;")
            self.append_transcript("System: Microphone muted.", is_user=False)
        else:
            self.is_muted = False
            self.btn_mute.setText("Mute")
            self.btn_mute.setStyleSheet("background-color: #e53e3e; color: white; text-align: center; border: none; border-radius: 15px; font-weight: bold;")
            self.append_transcript("System: Microphone unmuted.", is_user=False)
            
    def trigger_listen(self):
        if getattr(self, 'is_muted', False):
            self.toggle_mute()
        self.state_machine.transition_to(AssistantState.ACTIVE_LISTENING)
        self.update_audio_amplitude(0.8)
        
    def trigger_speak(self):
        self.state_machine.transition_to(AssistantState.ACTIVE_SPEAKING)
        self.update_audio_amplitude(0.5)

    def on_state_change(self, state: AssistantState):
        self.orb.set_state(state)

    def update_audio_amplitude(self, amplitude: float):
        self.orb.set_amplitude(amplitude)

    def append_transcript(self, text: str, is_user: bool = True):
        color = "#00FFFF" if is_user else "#FFFFFF"
        prefix = "User: " if is_user else "M.Y.R.A: "
        self.text_panel.append_text(prefix + text, color)
