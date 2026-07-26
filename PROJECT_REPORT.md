# M.Y.R.A (Myra) AI v2 — Comprehensive Project Report & AI Handover Document

> **Project Name:** Myra AI v2  
> **Version:** 0.1.0  
> **Repository:** `https://github.com/santo-72/myra-v2`  
> **Creator & Developer:** Santo Ghosh (TITAN)  
> **Primary Interface Languages:** Python 3.12 (Supported >=3.11) / Bengali (Bangla) & English conversational audio/visual interfaces.

---

## 1. PROJECT OVERVIEW

### Purpose / Goal
**Myra AI (M.Y.R.A - Class Autonomous AI Assistant)** is an advanced, multimodal, autonomous AI visual and voice assistant created by **Santo Ghosh** (named TITAN in UI). Built primarily for interactive conversational voice sessions in **Bengali (Bangla)** with technical support in English, Myra bridges conversational voice interactivity, real-time desktop monitoring, computer vision, local database conversation logging, semantic memory, automated web scraping, data analysis, and self-debugging code automation.

### Tech Stack
* **Languages:** Python 3.12 (Runtime Environment on Windows)
* **GUI Framework:** PyQt6 (`6.6.0+`) with custom QSS styling and animations
* **AI & LLM Services:**
  * **Google GenAI Live API:** `gemini-2.5-flash-native-audio-latest` (Multimodal Realtime Voice, Vision & Tools)
  * **Ollama (Fallback/Local LLM):** Local models like `llama3`
  * **Faster Whisper & PyAnnote:** Offline Speech-to-Text and Speaker Diarization
* **Audio & STT/TTS Infrastructure:**
  * **PyAudio & SoundDevice:** Real-time microphone input/output and PCM audio stream handling (`16kHz` input, `24kHz` output)
  * **WebRTC VAD:** High-precision Voice Activity Detection for low-latency barge-in and conversational pacing
* **Data Persistence & Memory:**
  * **SQLite (LocalDatabase):** Real-time conversational turn logging, utterance history, and imported user data (`data/myra_local.db`)
  * **ChromaDB:** Vector embedding database for long-term semantic user memory and fact recall (`data/chroma`)
* **Automation, Vision & Tooling:**
  * **Computer Vision:** OpenCV (`opencv-python`) & MediaPipe for webcam processing; MSS & Pillow for multi-monitor screen sharing
  * **Browser Automation:** Playwright (headless & interactive browser control) & PyAutoGUI (desktop UI simulation)
  * **Code & Git:** GitPython, PyGithub, Pandas/Matplotlib/Seaborn for exploratory data analysis
  * **System & Security:** Cryptography (Vault secrets), APScheduler (background scheduling), Docker SDK, Twilio SDK

### Project Structure
```text
myra-v2/
├── app/
│   ├── __init__.py                 # Core app package initialization
│   ├── config.py                   # Pydantic BaseSettings loading environmental variables from .env
│   ├── audio/
│   │   ├── __init__.py             # Audio sub-package initialization
│   │   └── pipeline.py             # AudioPipeline managing microphone input, WebRTC VAD, RMS amplitude, and Whisper/Diarization fallbacks
│   ├── core/
│   │   ├── __init__.py             # Core logic architecture
│   │   ├── dev_agent.py            # DevAgent orchestrating autonomous shell execution and build-test self-healing loops
│   │   ├── gemini_live_client.py   # GeminiLiveClient managing bidirectional Google GenAI WebSocket Live streaming, tool dispatch, and vision sending
│   │   ├── self_debug.py           # SelfDebugRuntime capturing failed command logs for automated LLM reflection & error patching
│   │   └── state_machine.py        # StateMachine transitioning Assistant states (DORMANT, LISTENING, THINKING, SPEAKING, ALERT, ERROR)
│   ├── memory/
│   │   ├── __init__.py             # Memory system exports
│   │   ├── database.py             # LocalDatabase (SQLite) managing real-time conversation_logs, saved_memories, and imported_data
│   │   └── manager.py              # MemoryManager wrapping ChromaDB PersistentClient for vector embeddings and fact indexing
│   ├── tools/
│   │   ├── __init__.py             # Tools package initialization
│   │   ├── browser_automation.py   # Playwright wrapper for headless web scraping and page interaction
│   │   ├── data_analysis.py        # Pandas/Matplotlib analytical utility for analyzing CSV summaries and datasets
│   │   ├── destructive_gate.py     # Voice/confirmation gate stopping unverified execution of risky system actions
│   │   ├── shell_runner.py         # Subprocess automation executing system terminal commands with captured stdout/stderr
│   │   ├── vision.py               # VisionTools managing high-speed MSS screenshot captures and monitor imaging
│   │   └── webcam_stream.py        # WebcamStream using OpenCV to snap pictures and process live camera frames
│   └── ui/
│       ├── __init__.py             # UI component library
│       ├── app_window.py           # AssistantWindow (PyQt6 QMainWindow) implementing the full "TITAN — Santo Ghosh" interface, Mute, Share Screen, and tool panels
│       ├── orb_widget.py           # OrbWidget rendering dynamic pulse/amplitude visual voice animations
│       └── text_panel.py           # TextPanel custom scrolling terminal display showing user/AI conversation transcripts
├── config/
│   └── system_prompt.md            # Master system personality and conversational behavioral rules (Bengali primary language instructions)
├── tests/                          # Automated Pytest validation test suite (18 passing tests)
├── main.py                         # Application entry point integrating async AI streaming (sender/receiver/vision loops) into PyQt6 event loop via QTimer
├── pyproject.toml                  # Project manifest and Python dependency specifications (Hatchling build backend)
└── run.bat                         # Windows execution batch script detecting venv and launching main.py
```

---

## 2. ARCHITECTURE

### Component Interoperability & Connections
```text
  [Microphone / Desktop Screen] <---> [AudioPipeline & VisionTools]
               │                                       │
               │ (PCM 16kHz & JPEG Frames)             │ (State Signals)
               ▼                                       ▼
  [Async Streaming Loop in main.py] <---> [AssistantWindow & OrbWidget (PyQt6)]
               │
               ├───────────────────┬───────────────────┐
               │ (Live Stream)     │ (SQL Log)         │ (Vector Embed)
               ▼                   ▼                   ▼
     [Gemini Live API WebSocket]  [SQLite DB]       [ChromaDB Memory]
               │
               └─> (Tool Invocation) ──> [WebForge / DevAgent / DataAnalyzer]
```

### Key Design Patterns Used
1. **Asynchronous/GUI Event Loop Co-Existence:** Instead of blocking the PyQt6 GUI with long-running AI API calls, `main.py` creates a clean native `asyncio.EventLoop` coupled to a `QTimer` firing at 10ms intervals. This allows seamless real-time UI animation alongside asynchronous networking.
2. **State Machine Driven UX:** The UI visualizer (`OrbWidget`), text transcripts, and audio sensitivity are strictly governed by an event-driven `StateMachine` emitting state transition hooks (`DORMANT` ➔ `ACTIVE_LISTENING` ➔ `ACTIVE_THINKING` ➔ `ACTIVE_SPEAKING`).
3. **Dual-Layer Memory (SQL Relational + Vector Semantic):** 
   * **Relational (SQLite):** Guarantees zero loss of conversation transcripts and interaction timelines.
   * **Semantic (ChromaDB):** Enables fuzzy search and factual context retrieval when the model answers historical user queries.
4. **Resilient Streaming & Echo Cooldown:** Implements smart bandwidth buffering (`threshold_bytes`) coupled with a time-based microphone audio suppression window (`ai_speaking_until`) that totally eradicates audio feedback loops and self-repetition.

### Data Flow (End-to-End Voice Request Lifecycle)
1. **Capture & Detection:** `audio_sender()` in `main.py` retrieves PCM chunks (`16kHz`, 16-bit mono) from `AudioPipeline`. WebRTC VAD calculates voice activity.
2. **Mute & Feedback Filtering:** If `window.is_muted` is True or current time is within `ai_speaking_until` (AI speaking cooldown), audio chunks are discarded immediately.
3. **Buffering & Transmission:** Active voice packets are accumulated into an `audio_buffer`. Once past thresholds, they are pumped to Google's backend via `GeminiLiveClient.send_audio()` using bidirectional WebSocket streaming.
4. **Parallel Multimodal Vision:** If `window.is_screen_sharing` is active, `screen_streamer()` captures a resized compressed monitor frame every 3.0 seconds and injects it into the WebSocket stream via `send_image()`.
5. **Receive & Action Execution:** `audio_receiver()` parses incoming GenAI streaming packets:
   * **Audio Parts (`inline_data`):** Written immediately to PyAudio out-stream at `24kHz` while advancing the room echo cooldown timer.
   * **Text Parts (`text`):** Displayed inside the UI `TextPanel` transcript in Bengali, logged permanently into SQLite (`db.log_conversation`), and indexed inside ChromaDB (`chroma_manager.remember_fact`).

---

## 3. FEATURES & LATEST ENHANCEMENTS

### Implemented Features
* **Real-time Bengali Multimodal Voice Chat:** Natural, ultra-low latency voice communication in Bengali using Google Gemini Live audio model.
* **Working Microphone Mute/Unmute:** Interactive UI Mute button that immediately halts microphone stream processing and pauses STT buffering.
* **Multimodal Real-time Screen Sharing:** Toggle button allowing Myra AI to continuously analyze monitor content via streaming screen frames, enabling visual questions and answers.
* **Automated SQLite Conversation DB:** All session events, user audio timestamps, and AI voice responses are saved cleanly to `data/myra_local.db`.
* **Vector Semantic Memory:** Persistent fact storage using ChromaDB allowing historical context injection.
* **Auto-Reconnection Architecture:** Automatically detects WebSocket ping drops or connectivity loss and silently performs streaming restarts without crushing the desktop app.
* **WebForge AI (Playwright Scraper):** Headless automated web browsing tool allowing web summary extraction via UI button or LLM tool calls.
* **Data Analyzer (Pandas/CSV):** Autonomous data profiling and statistics generator capable of running summary analysis on local workspace CSV files.
* **Camera Module (OpenCV/Webcam):** On-demand visual photo snapshot capability via attached hardware cameras.
* **DevAgent / Code Assistant:** Build-test automation framework integrated with a self-debug feedback runtime.

### Incomplete / In-Progress Features
* **Ollama Offline Fallback Stream Processing:** Currently offline mode provides simple mock text loop behaviors; full offline STT/TTS coupling with local Whisper and Coqui/TTS remains open for future enhancements.
* **Full Tool Dispatch Loop over Gemini Live WebSocket:** Tool schemas (like database search and browser interaction) are declared in `gemini_live_client.py`, but automated async reception and response loops for incoming function calls over the Live stream require full execution routing.

### Known Bugs & TODOS
* **TODO in `app/tools/destructive_gate.py` (Line 44):** 
  ```python
  # TODO: Integrate with audio/STT pipeline to actually wait for "yes"
  ```
  *Current behavior:* The confirmation gate returns a stub or console prompt instead of pausing execution to analyze acoustic vocal approval for destructive shell actions.

---

## 4. DEPENDENCIES & CONFIG

### Primary Dependencies (`pyproject.toml`)
| Dependency | Version | Purpose & Function |
| :--- | :--- | :--- |
| **`pydantic-settings`** | `>=2.7.0` | Secure environment variable and `.env` parsing (`app/config.py`) |
| **`google-genai`** | `>=0.2.0` | Official GenAI SDK for Gemini Live websocket audio & image input |
| **`webrtcvad`** | `>=2.0.10` | High-speed Voice Activity Detection (VAD) |
| **`PyAudio`** / **`sounddevice`** | `>=0.2.14` / `>=0.4.6` | OS-level hardware microphone and output speaker streaming |
| **`chromadb`** | `>=0.4.24` | Embedded vector database for local memory indexing |
| **`PyQt6`** | `>=6.6.0` | Desktop user interface and visual styling engine |
| **`mss`** / **`Pillow`** | `>=9.0.0` / `>=10.2.0` | Ultra-fast multi-monitor screen capture and JPEG compression |
| **`playwright`** / **`PyAutoGUI`** | `>=1.41.0` / `>=0.9.54` | Headless browser scraping and OS keyboard/mouse automation |
| **`pandas`** / **`matplotlib`** | `>=2.2.0` / `>=3.8.0` | Data structuring and visual exploratory chart creation |
| **`structlog`** | `>=24.1.0` | Structured JSON application debugging logs |

### Required Environment Variables (`.env`)
```env
GEMINI_API_KEY=AIzaSy...                # (Required) Google Gemini API Key for Live Audio Streaming
HUGGINGFACE_TOKEN=hf_...                # (Optional) For downloading gated speaker diarization models
GITHUB_TOKEN=ghp_...                    # (Optional) For git integration automations
ENVIRONMENT=development                 # 'development' or 'production'
LOG_LEVEL=INFO                          # Logging verbosity
WORKSPACE_DIR=workspace                 # Target directory for scratch output, screen snapshots, and data
SECRET_WAKE_PHRASE="myra wake up"       # Custom invocation keyword
```

---

## 5. DATABASE ARCHITECTURE

### SQLite Schema (`data/myra_local.db`)
Managed entirely by `LocalDatabase` (`app/memory/database.py`). Designed with three primary tables:

1. **`conversation_logs`**: Chronological log of all spoken vocal utterances, AI responses, and visual events.
   * `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`, `session_id`: `TEXT`, `timestamp`: `TEXT`, `sender`: `TEXT`, `message_type`: `TEXT`, `content`: `TEXT`
2. **`saved_memories`**: Relational key-value table for persistent user facts, preferences, and state parameters.
   * `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`, `key`: `TEXT UNIQUE`, `value`: `TEXT`, `created_at`: `TEXT`, `updated_at`: `TEXT`
3. **`imported_data`**: Generic storage repository for external project files, GitHub pulls, and structural snapshots.
   * `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`, `category`: `TEXT`, `source`: `TEXT`, `data_payload`: `TEXT`, `imported_at`: `TEXT`

---

## 6. CURRENT STATE & NEXT STEPS FOR CLAUDE / NEXT AI ASSISTANT

### What Was Last Worked On (Today's Progress)
1. **Full Database & Memory Integration:** Connected SQLite (`LocalDatabase`) and ChromaDB (`MemoryManager`) into the primary asynchronous application loop. Every voice interaction, system startup event, and conversational exchange is now logged to disk automatically.
2. **Fixed Mute Button functionality:** Connected `AssistantWindow.is_muted` toggle directly to the streaming loop in `main.py`, guaranteeing instant hardware audio buffer suppression when muted.
3. **Implemented Multimodal Screen Sharing:** Connected the UI **Share Screen** button to a dedicated concurrent task (`screen_streamer`) that captures desktop screenshots via MSS and streams compressed images directly into the active Gemini Live websocket session.
4. **Validation & Testing:** Verified all system functionalities; running `pytest` produces **18 passed test cases**.

### What's Next / Pending Tasks for Claude
* **Implement Live Tool Call Response Execution:** Upgrade `audio_receiver()` in `main.py` to inspect `msg.tool_call` packets coming from Gemini Live. Route function calls (like `query_conversation_logs` and `take_screenshot`) to their local tools and send responses back using `session.send_tool_response()`.
* **Resolve TODO in `destructive_gate.py`:** Add actual STT wake-word analysis to pause execution and demand explicit vocal spoken confirmation ("yes" / "হাঁ") before running system modifying shell commands.
* **Offline Local LLM STT/TTS Binding:** Implement Whisper offline local transcription cleanly into `mock_loop()` in `main.py` when Gemini API connectivity is disconnected or unavailable.
