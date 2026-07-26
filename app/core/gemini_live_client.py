import asyncio
import structlog
from google import genai
from google.genai import types
from app.config import settings
from typing import AsyncGenerator

logger = structlog.get_logger(__name__)

class GeminiLiveClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None
        self.session = None
        self.model_name = "gemini-2.5-flash-native-audio-latest"
        self.db = None
        self.chroma_manager = None
        self.session_id = None
        
        # Load system prompt
        self.system_instruction = "You are an AI."
        try:
            with open("config/system_prompt.md", "r", encoding="utf-8") as f:
                self.system_instruction = f.read()
        except FileNotFoundError:
            pass

    def set_database(self, db, chroma_manager, session_id):
        self.db = db
        self.chroma_manager = chroma_manager
        self.session_id = session_id

    async def connect(self):
        if not self.client:
            logger.error("no_gemini_api_key")
            return False

        tool_declarations = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="run_shell_command",
                        description="Executes a shell command in the sandboxed workspace.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"command": types.Schema(type=types.Type.STRING)}
                        )
                    ),
                    types.FunctionDeclaration(
                        name="read_file",
                        description="Reads a file from the workspace.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"file_path": types.Schema(type=types.Type.STRING)}
                        )
                    ),
                    types.FunctionDeclaration(
                        name="write_file",
                        description="Writes content to a file in the workspace.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "file_path": types.Schema(type=types.Type.STRING),
                                "content": types.Schema(type=types.Type.STRING)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="git_init",
                        description="Initializes a local git repository in the workspace."
                    ),
                    types.FunctionDeclaration(
                        name="git_commit",
                        description="Stages all files and commits them to the local git repository.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"message": types.Schema(type=types.Type.STRING)}
                        )
                    ),
                    types.FunctionDeclaration(
                        name="generate_project_scaffold",
                        description="Generates boilerplate code for a new project in the workspace.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "project_name": types.Schema(type=types.Type.STRING),
                                "stack": types.Schema(type=types.Type.STRING)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="analyze_csv_summary",
                        description="Analyzes a CSV file and returns its descriptive statistics.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={"file_path": types.Schema(type=types.Type.STRING)}
                        )
                    ),
                    types.FunctionDeclaration(
                        name="plot_basic_chart",
                        description="Plots a basic chart (bar, line, scatter) from a CSV file.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "file_path": types.Schema(type=types.Type.STRING),
                                "x_column": types.Schema(type=types.Type.STRING),
                                "y_column": types.Schema(type=types.Type.STRING),
                                "chart_type": types.Schema(type=types.Type.STRING),
                                "output_filename": types.Schema(type=types.Type.STRING)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="take_screenshot",
                        description="Takes a screenshot of the user's primary monitor and saves it to the workspace.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "output_filename": types.Schema(type=types.Type.STRING)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="schedule_task",
                        description="Schedules a task to run in the background.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "task_name": types.Schema(type=types.Type.STRING),
                                "trigger": types.Schema(type=types.Type.STRING),
                                "interval_seconds": types.Schema(type=types.Type.INTEGER)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="get_system_telemetry",
                        description="Returns hardware metrics (CPU, RAM, Disk)."
                    ),
                    types.FunctionDeclaration(
                        name="get_page_content",
                        description="Fetches the content of a web page using a headless browser.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "url": types.Schema(type=types.Type.STRING)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="gui_move_mouse",
                        description="Moves the mouse to specific screen coordinates.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "x": types.Schema(type=types.Type.INTEGER),
                                "y": types.Schema(type=types.Type.INTEGER)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="gui_click",
                        description="Clicks the mouse at current or specified coordinates.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "x": types.Schema(type=types.Type.INTEGER),
                                "y": types.Schema(type=types.Type.INTEGER)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="gui_type_text",
                        description="Types text into the active window.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "text": types.Schema(type=types.Type.STRING)
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="query_conversation_logs",
                        description="Searches previous voice conversation logs and transcripts in the local SQLite database.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "query": types.Schema(type=types.Type.STRING, description="Keyword or phrase to search for in past discussions.")
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="save_user_memory",
                        description="Saves important user preferences, facts, or information directly into the local SQLite database.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "key": types.Schema(type=types.Type.STRING, description="Name or identifier of the memory (e.g. user_favorite_color)"),
                                "value": types.Schema(type=types.Type.STRING, description="The fact or details to remember")
                            }
                        )
                    ),
                    types.FunctionDeclaration(
                        name="get_saved_memories",
                        description="Retrieves all stored facts, profile details, and important memories from the local database."
                    ),
                    types.FunctionDeclaration(
                        name="send_message",
                        description="Sends an automated text message via WhatsApp, Messenger, or Telegram to a recipient.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "app": types.Schema(type=types.Type.STRING, enum=["whatsapp", "messenger", "telegram"], description="Target messaging application"),
                                "recipient": types.Schema(type=types.Type.STRING, description="Name of the contact or recipient to message"),
                                "message": types.Schema(type=types.Type.STRING, description="The message content to send")
                            },
                            required=["app", "recipient", "message"]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="add_contact",
                        description="Saves a new person's contact number or username into Myra's local SQLite contacts database.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "name": types.Schema(type=types.Type.STRING, description="Name of the person or contact"),
                                "app": types.Schema(type=types.Type.STRING, enum=["whatsapp", "messenger", "telegram", "phone"], description="Messaging app or platform (default to whatsapp for mobile numbers)"),
                                "identifier": types.Schema(type=types.Type.STRING, description="Phone number or username/ID")
                            },
                            required=["name", "app", "identifier"]
                        )
                    ),
                    types.FunctionDeclaration(
                        name="list_contacts",
                        description="Retrieves all saved contact names, phone numbers, and messaging apps from the local SQLite database.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "app": types.Schema(type=types.Type.STRING, description="Optional app filter (e.g. whatsapp, messenger)")
                            }
                        )
                    )
                ]
            )
        ]

        config = types.LiveConnectConfig(
            system_instruction=self.system_instruction,
            tools=tool_declarations,
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            temperature=0.5
        )
        try:
            # We use client.aio for asynchronous streaming
            self._live_ctx = self.client.aio.live.connect(model=self.model_name, config=config)
            self.session = await self._live_ctx.__aenter__()
            logger.info("gemini_live_connected")
            return True
        except Exception as e:
            logger.error("gemini_connection_error", error=str(e))
            return False

    def is_connected(self) -> bool:
        return self.session is not None

    async def reconnect(self) -> bool:
        logger.info("gemini_live_reconnecting")
        await self.disconnect()
        await asyncio.sleep(1)
        return await self.connect()

    async def send_audio(self, pcm_data: bytes) -> bool:
        if not self.session:
            return False
        
        try:
            await self.session.send_realtime_input(
                audio=types.Blob(
                    data=pcm_data,
                    mime_type="audio/pcm;rate=16000"
                )
            )
            return True
        except Exception as e:
            logger.error("send_audio_error", error=str(e))
            self.session = None
            self._live_ctx = None
            return False

    async def send_image(self, image_data: bytes, mime_type: str = "image/jpeg") -> bool:
        if not self.session:
            return False
        try:
            await self.session.send_realtime_input(
                media=types.Blob(
                    data=image_data,
                    mime_type=mime_type
                )
            )
            return True
        except Exception as e:
            logger.error("send_image_error", error=str(e))
            return False

    async def receive_stream(self) -> AsyncGenerator[types.LiveServerMessage, None]:
        if not self.session:
            return
            
        try:
            async for message in self.session.receive():
                yield message
        except Exception as e:
            logger.error("receive_stream_error", error=str(e))
            self.session = None
            self._live_ctx = None
            
    async def disconnect(self):
        try:
            if hasattr(self, '_live_ctx') and self._live_ctx:
                await self._live_ctx.__aexit__(None, None, None)
        except Exception as e:
            logger.warning("error_during_disconnect", error=str(e))
        finally:
            self._live_ctx = None
            self.session = None
            logger.info("gemini_live_disconnected")
