import os
import shutil
import structlog
from pathlib import Path
from app.config import settings

logger = structlog.get_logger(__name__)

class FileSystemTools:
    def __init__(self):
        self.workspace_root = Path(settings.workspace_dir).resolve()
        
        # Create workspace if it doesn't exist
        if not self.workspace_root.exists():
            self.workspace_root.mkdir(parents=True)
            logger.info("workspace_created", path=str(self.workspace_root))

    def _safe_path(self, relative_path: str) -> Path:
        """Resolves path and ensures it remains within the workspace root."""
        # Strip leading slashes to prevent absolute path bypasses in Windows/Linux
        clean_path = relative_path.lstrip("/").lstrip("\\")
        target_path = (self.workspace_root / clean_path).resolve()
        
        try:
            target_path.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(f"Access Denied: Path '{relative_path}' is outside the sandbox workspace.")
            
        return target_path

    def read_file(self, file_path: str) -> str:
        safe_path = self._safe_path(file_path)
        if not safe_path.exists():
            return f"Error: File '{file_path}' does not exist."
        if not safe_path.is_file():
            return f"Error: '{file_path}' is a directory, not a file."
            
        try:
            with open(safe_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def write_file(self, file_path: str, content: str) -> str:
        safe_path = self._safe_path(file_path)
        
        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = safe_path.with_name(f"{safe_path.name}.tmp_{os.getpid()}")
            
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                # Atomic replacement of target file to prevent corrupted partial writes upon interruption
                temp_path.replace(safe_path)
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                        
            logger.info("file_written_atomically", path=file_path)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            logger.error("file_write_error", path=file_path, error=str(e))
            return f"Error writing file: {str(e)}"

    def list_directory(self, dir_path: str = ".") -> str:
        safe_path = self._safe_path(dir_path)
        
        if not safe_path.exists():
            return f"Error: Directory '{dir_path}' does not exist."
        if not safe_path.is_dir():
            return f"Error: '{dir_path}' is not a directory."
            
        try:
            items = os.listdir(safe_path)
            return "\n".join(items) if items else "Directory is empty."
        except Exception as e:
            return f"Error listing directory: {str(e)}"

    def delete_path(self, path: str) -> str:
        safe_path = self._safe_path(path)
        
        if not safe_path.exists():
            return f"Error: Path '{path}' does not exist."
            
        try:
            if safe_path.is_dir():
                shutil.rmtree(safe_path)
            else:
                safe_path.unlink()
            logger.info("path_deleted", path=path)
            return f"Successfully deleted {path}"
        except Exception as e:
            logger.error("delete_error", path=path, error=str(e))
            return f"Error deleting path: {str(e)}"
