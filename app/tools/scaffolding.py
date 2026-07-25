import structlog
from pathlib import Path
from app.config import settings

logger = structlog.get_logger(__name__)

class ScaffoldingEngine:
    def __init__(self):
        self.workspace_root = Path(settings.workspace_dir).resolve()

    def generate_project_scaffold(self, project_name: str, stack: str) -> str:
        """
        Generates basic project boilerplate in the workspace.
        Supported stacks: 'fastapi', 'flask'
        """
        target_dir = self.workspace_root / project_name
        
        if target_dir.exists():
            return f"Error: Project '{project_name}' already exists."
            
        try:
            target_dir.mkdir(parents=True)
            
            if stack.lower() == "fastapi":
                self._scaffold_fastapi(target_dir)
            elif stack.lower() == "flask":
                self._scaffold_flask(target_dir)
            else:
                return f"Error: Unsupported stack '{stack}'. Try 'fastapi' or 'flask'."
                
            logger.info("project_scaffolded", project_name=project_name, stack=stack)
            return f"Successfully generated {stack} boilerplate in '{project_name}'"
        except Exception as e:
            logger.error("scaffold_error", error=str(e))
            return f"Error generating project: {str(e)}"

    def _scaffold_fastapi(self, target_dir: Path):
        (target_dir / "main.py").write_text(
            "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef read_root():\n    return {'Hello': 'World'}\n",
            encoding="utf-8"
        )
        (target_dir / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")

    def _scaffold_flask(self, target_dir: Path):
        (target_dir / "app.py").write_text(
            "from flask import Flask\n\napp = Flask(__name__)\n\n@app.route('/')\ndef hello():\n    return 'Hello World!'\n",
            encoding="utf-8"
        )
        (target_dir / "requirements.txt").write_text("Flask\n", encoding="utf-8")
