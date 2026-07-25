# JARVIS / M.Y.R.A-Class Autonomous AI Assistant — Master Build Plan (Python 3.12+)

## 0. Project Overview

**Goal:** Build a private, voice-native, autonomous AI assistant ("the Assistant") inspired by JARVIS / M.Y.R.A, built on **Python 3.12+** and using the **Google Gemini Multimodal Live API** as the reasoning/voice core. The Assistant must remain in a secure dormant state until it verifies (a) a specific secret wake phrase AND (b) the speaker's voiceprint, ignoring all other audio input. Once active, it can converse in real time with human-like voice dynamics, control the local OS, write and debug full software projects, push to GitHub, analyze data, and see the screen.

**Owner is a non-coder.** This plan is written to be executed autonomously by an AI coding agent (Cursor / Antigravity / Claude Code, etc.) inside this repository. Every phase must be fully working and tested before the next phase begins.

**Core tenets:**
- **Python 3.12+ Standard:** Fully optimized for Python 3.12+ async features, modern `typing` (e.g., `type` aliases, structural pattern matching), and native performance enhancements.
- **Single-user only.** No voice other than the enrolled owner's voiceprint should ever trigger an action, regardless of what it says.
- **Dormant-by-default.** No audio is acted upon (not even logged in plaintext transcripts) until both the secret phrase and the voiceprint check pass.
- **Local-first privacy.** Voiceprint embeddings, the secret phrase, and conversation memory are stored locally, encrypted at rest, and never leave the machine except for the live audio/video stream sent to the Gemini API after authentication.
- **M.Y.R.A-Style Natural Voice:** Natural pitch modulation, conversational pacing, realistic pauses/fillers, zero robotic cadence, and seamless barge-in capability.
- **Confirm before destroy.** Any irreversible OS/file/git action requires an explicit spoken confirmation step.
- **Sequential build.** Each phase produces a runnable, tested increment. Do not skip ahead.

---

## 1. Tech Stack Summary (Python 3.12+ Compatible)

| Layer | Technology |
|---|---|
| Runtime | Python 3.12+ |
| Realtime AI Core | Google Gemini Multimodal Live API via `google-genai` SDK (`client.aio.live.connect`) |
| Speaker Recognition | `pyannote.audio` / `speechbrain` (ECAPA-TDNN) + Deepfake Anti-Spoofing Filter |
| Wake / Secret Phrase | Local low-latency STT pass (`faster-whisper` tiny/base model or `openWakeWord`) |
| Audio I/O | `sounddevice` / `PyAudio`, `webrtcvad` / Silero VAD, YAMNet for Environmental Sound Classification |
| Realtime Transport | Python native `asyncio` + `websockets` for internal service communication |
| Memory | `ChromaDB` (local vector store) + Graph DB (`KuzuDB` / local `Neo4j`) |
| Desktop & AR UI | `PyQt6` (animated "Orb" widget via `QPainter`), OpenVR / WebXR HUD Streamer |
| OS & Automation | `subprocess`, `psutil`, `playwright`, `pyautogui`, `docker` (Python SDK) |
| Dev Agent & IDE | `GitPython` + `PyGithub`, `bpy` (Blender API wrapper), VS Code LSP Bridge |
| Data & Payments | `pandas`, `matplotlib` / `seaborn`, Lightning/Solana Micropayments SDK |
| Vision / Screen | `mss` + `Pillow`, `pytesseract`, OpenCV + MediaPipe for gaze & posture tracking |
| Security & Net | Nmap / Scapy, Post-Quantum Encrypted Vault (`pqcrypto` / `cryptography.fernet`) |
| Observability | `structlog` + OpenTelemetry, Local Metrics Dashboard |

---

## Phase 1: Core Architecture, Speaker Recognition & Live API Setup

- [ ] **1.1 Project Scaffolding:** Set up Python 3.12+ project structure (`/app`, `/app/core`, `/app/audio`, `/app/auth`, `/app/memory`, `/app/tools`, `/app/ui`, `/tests`, `/config`, `/data`), `pyproject.toml`, `.env.example`, and robust `config.py`.
- [ ] **1.2 Audio Capture Pipeline:** Continuous mic stream via `sounddevice`, VAD speech detection (`webrtcvad`/Silero), and streaming PCM audio output via `audio/playback.py`.
- [ ] **1.3 Secret Activation Phrase:** Local offline STT (`faster-whisper`) running continuously on dormant buffer. Hash-based secret phrase matching with fuzzy tolerance.
- [ ] **1.4 Voice Biometrics:** Guided enrollment script (`auth/enroll_voice.py`) generating speaker embedding using `pyannote.audio`. Cosine similarity check above threshold required before leaving dormant state.
- [ ] **1.5 State Machine:** Explicit states (`DORMANT` -> `AUTHENTICATING` -> `ACTIVE_LISTENING` -> `ACTIVE_THINKING` -> `ACTIVE_SPEAKING` -> `DORMANT`).
- [ ] **1.6 Gemini Multimodal Live API & M.Y.R.A Voice Setup:** 
  - Native bidirectional streaming client (`core/gemini_live_client.py`) using `google-genai` SDK on Python 3.12 `asyncio`.
  - Configure native audio modality with warm, human-like voice profile (`Aoede` / `Puck` or custom audio configuration).
  - Inject M.Y.R.A-style speech guidelines into `config/system_prompt.md` for realistic pitch modulation, natural pauses, and conversational flow.
- [ ] **1.7 Long-Term Memory:** Persistent local ChromaDB with `remember_fact` and `recall_facts` function tools.
- [ ] **1.8 Internal Service Layer:** Async WebSocket server (`core/ws_server.py`) decoupling AI core from UI.

---

## Phase 2: Interface & Voice Layer

- [ ] **2.1 PyQt6 Application Shell:** Frameless, always-on-top transparent desktop window with system tray controls (Python 3.12 compatibility checked).
- [ ] **2.2 Animated Orb Widget:** Custom `QPainter` widget dynamically reflecting AI states and reacting to audio amplitude.
- [ ] **2.3 M.Y.R.A-Style Smart Barge-In:** Low-latency interruption system that instantly cancels outgoing audio and streams new speech ONLY when the verified owner's voice interrupts mid-sentence.
- [ ] **2.4 Text Panel & UI Feedback:** Collapsible transcript display, text input fallback, and neutral non-revealing visual cues on failed auth.

---

## Phase 3: Autonomous Workspace & OS Execution

- [ ] **3.1 Tool-Calling Schema:** Function calling tools (`run_shell_command`, `read_file`, `write_file`, `list_directory`, `delete_path`).
- [ ] **3.2 Sandboxed Execution:** Subprocess wrapper with working directory limits and audit logging.
- [ ] **3.3 Destructive Action Gate:** Spoken confirmation requirement for risky system actions (`rm`, `sudo`, force-push).
- [ ] **3.4 Self-Debugging Runtime:** Auto-captures tracebacks, feeds errors back to Gemini, patches code, and retries up to max limit.

---

## Phase 4: Full-Stack DevAgent Capabilities

- [ ] **4.1 Scaffolding Engine:** Multi-file project generation based on Python 3.12+ stack starters (FastAPI, React, Flask, Next.js) with unified diff previews.
- [ ] **4.2 Git & GitHub Integration:** `GitPython` and `PyGithub` tools for commits, PRs, issues, and repository creation.
- [ ] **4.3 Build-Test-Fix Loop:** Automatic installation of dependencies, running tests, and applying self-debugging before marking tasks complete.

---

## Phase 5: Advanced Data Analysis & Vision

- [ ] **5.1 Data Analysis & Charts:** Safe `pandas` query tools + `matplotlib`/`seaborn` chart generation.
- [ ] **5.2 Screen Capture & OCR:** Opt-in real-time screen streaming (`mss` + `Pillow`) and targeted OCR extraction (`pytesseract`).
- [ ] **5.3 Vision-Triggered Actions:** Diagnosing visual errors on screen and triggering self-fix routines in active files.

---

## Phase 6: Proactive Intelligence, Swarm Architecture & Smart Ecosystem

### 6.1 Proactive AI & Autonomous Scheduler
- [ ] Implement `tools/scheduler.py`: Background cron-like system (`APScheduler` / `asyncio` task loop) for scheduled tasks.
- [ ] Implement Proactive Notification Engine: Voice/visual interruptions for urgent alerts (calendar, high CPU/GPU temp, build failures).
- [ ] Add `config/recurring_tasks.json` for daily automated routines (e.g., GitHub issue summaries, news digest).

### 6.2 Advanced OS, Browser & GUI Automation
- [ ] Implement `tools/browser_automation.py` using `Playwright` for web browsing, scraping, and web app testing.
- [ ] Implement `tools/gui_automation.py` using `pyautogui` for OS-level mouse/keyboard actions when CLI tools are unavailable.
- [ ] Mandatory spoken confirmation gate for sensitive browser actions (e.g., payment forms, password entries).

### 6.3 Multi-Agent Swarm Integration
- [ ] Build `core/agent_swarm.py`: Orchestrator delegating multi-step tasks to specialized sub-agents (*Architect*, *Coder*, *Tester*).
- [ ] Implement inter-agent communication pipeline to synthesize solutions before responding to the Live API session.

### 6.4 Knowledge Graph & Cross-Session Workspace Context
- [ ] Combine ChromaDB with local Graph DB (`KuzuDB` or local `Neo4j`) in `memory/knowledge_graph.py` to map deep semantic relationships.
- [ ] Implement auto-restoration of workspace state: track open files, terminals, and active tasks across system reboots.

### 6.5 Smart Home & System Telemetry
- [ ] Implement `tools/smart_home.py`: Home Assistant REST/WebSocket API integration for voice-controlled IoT devices.
- [ ] Implement `tools/system_telemetry.py` (`psutil` / `GPUtil`) for real-time hardware monitoring.

### 6.6 Zero-Knowledge Vault & Network Sandbox
- [ ] Build `auth/vault.py`: Encrypted storage (`cryptography.fernet`) for API keys and tokens, unlocked only during active sessions.
- [ ] Outbound network safety checks to block unauthorized outgoing requests during automated code executions.

---

## Phase 7: Edge AI, Telephony & Spatial Intelligence

### 7.1 WebCam & Physical Environment Awareness
- [ ] Implement `tools/webcam_stream.py`: Optional external camera feed input for room-level object tracking and physical presence detection.
- [ ] Implement Adaptive Voice Modulation: Automatically lower playback volume and shift to a whispered/soft voice mode during late hours.

### 7.2 Telephony & Communication Automation
- [ ] Implement `tools/telephony.py` via Twilio / VoIP API: Make/receive real voice calls for scheduling or urgent spoken alerts.
- [ ] Implement `tools/comms_copilot.py`: Read and draft responses for Slack, WhatsApp Web, and Gmail with human confirmation before sending.

### 7.3 Offline Hybrid Fallback (Local LLM)
- [ ] Implement `core/offline_fallback.py`: Route basic offline OS commands to a local LLM (`Ollama` / `llama.cpp`) when internet drops.

### 7.4 Security Decoy & Emergency Lockdown
- [ ] Implement Decoy Mode (Duress Trigger): Instantly switch to a dummy workspace and isolated memory state if a specific emergency duress phrase is spoken.
- [ ] Implement Panic Lockdown: Purge session keys and lock local databases upon multiple consecutive unauthorized access attempts.

---

## Phase 8: Advanced Sound Perception & Isolated Code Interpreter

### 8.1 Environmental Sound & Scene Recognition
- [ ] Implement `audio/sound_classifier.py` using `YAMNet`: Detect ambient sound events (glass breaking, door knocking, alarms) while in dormant state.
- [ ] Wire ambient sound triggers to safety alerts or proactive spoken warnings.

### 8.2 Docker / Wasm Isolated Execution Sandbox
- [ ] Implement `tools/isolated_runner.py` using `docker` Python SDK: Execute untrusted code snippets in an isolated container to protect the host OS.
- [ ] Integrate isolated runner with Phase 3 self-debug loop before running scripts on host machine.

---

## Phase 9: Generative 3D CAD, AR HUD & Health Telemetry

### 9.1 Voice-Driven CAD & 3D Modeling Engine
- [ ] Implement `tools/cad_automation.py` interfacing with `Blender` (`bpy`) / `FreeCAD`: Generate 3D object models and designs from prompts.
- [ ] Export generated models (`.STL`, `.OBJ`) automatically to a preview directory or 3D printer queue.

### 9.2 Augmented Reality (AR) Overlay Stream
- [ ] Implement `ui/ar_hud_streamer.py`: Stream minimalist HUD status and widgets to secondary displays or WebXR/OpenVR protocols.

### 9.3 Ergonomic & Ergostress Health Monitoring
- [ ] Implement `tools/health_monitor.py` using `MediaPipe` pose & face mesh: Monitor posture, eye fatigue, and prolonged sitting with polite reminders.

---

## Phase 10: Anti-Spoofing, BCI Integration & Edge Mesh Grid

### 10.1 AI-Voice Anti-Spoofing Guard
- [ ] Implement `auth/anti_spoofing.py`: Add synthetic audio detection (spectral flux & phase analysis) alongside voice biometrics to prevent AI-cloned voice attacks from triggering the assistant.

### 10.2 BCI & Focus State Telemetry
- [ ] Implement `tools/bci_telemetry.py` (via LSL / BrainFlow): Read focus/fatigue metrics from consumer BCI headbands (e.g., OpenBCI, Muse) to modulate assistant response verbosity dynamically.

### 10.3 Multi-Device Local Mesh Grid
- [ ] Implement `core/mesh_node.py` using WebRTC/gRPC: Connect secondary local devices (laptops, Raspberry Pis) to distribute background workloads off the main CPU.

---

## Phase 11: Autonomous Web Paywalls & Post-Quantum Security

### 11.1 Agentic Micro-Transactions Wallet
- [ ] Implement `tools/crypto_wallet.py` (Solana / Bitcoin Lightning Network): Provide the Assistant with a controlled, sandboxed micro-wallet to pay for developer API paywalls autonomously up to a pre-set daily limit.

### 11.2 Quantum-Resistant Vault & Forensic Purge
- [ ] Upgrade `auth/vault.py` with post-quantum cryptography libraries (`pqcrypto`).
- [ ] Implement anti-forensic purge routines: Instantly overwrite sensitive vector memory and session tokens in RAM/disk during emergency lockdown state.

---

## Phase 12: Automated Disaster Recovery & Thermal-Aware Computing

### 12.1 Self-Healing System Recovery
- [ ] Implement `tools/disaster_recovery.py`: Automated snapshot generation (Git/ChromaDB state) prior to any system-level code execution.
- [ ] Implement auto-rollback protocol: Restore system state automatically if a self-debugging task corrupts local runtime environment.

### 12.2 Thermal & Power Efficiency Scaling
- [ ] Implement `tools/power_manager.py`: Monitor device battery status and thermal throttling. Automatically shift heavy computational jobs (e.g., video streaming/OCR) to lighter offline models when running on battery power.

---

## Phase 13: Voice-Native IDE Bridge & Security Auditor

### 13.1 IDE Context Integration (VS Code / JetBrains Bridge)
- [ ] Implement `tools/ide_bridge.py` using WebSocket/LSP Protocol: Allow the Assistant to read active cursor context, highlighted code blocks, and open tabs directly within the user's active code editor.
- [ ] Voice-driven refactoring: Speak commands like *"Refactor this highlighted function to be asynchronous"* directly into the IDE interface.

### 13.2 Automated Network & Vulnerability Auditor
- [ ] Implement `tools/security_auditor.py` (wrapping `nmap` / `scapy` / `bandit`): Periodically audit open local ports, weak environment variables, and vulnerable Python dependencies, outputting actionable security patch suggestions.

---

## Phase 14: System Observability, Rate-Limiting & Auto-Updater

### 14.1 Structured Telemetry & Structured Logging
- [ ] Implement `core/telemetry.py` using `structlog` & OpenTelemetry: Capture asynchronous traces of latency, API tokens, and tool usage in local, privacy-safe JSON logs.

### 14.2 API Rate-Limiter & Self-Throttling Guard
- [ ] Implement `core/rate_limiter.py`: Dynamic request queue that prevents Gemini Live API quota exhaustion by auto-budgeting token rates and pacing background agent tasks.

### 14.3 Self-Updating Core Engine
- [ ] Implement `tools/auto_updater.py`: Secure background routine that fetches the latest repository patches from a designated private Git remote, validates tests, and seamlessly hot-reloads internal services.