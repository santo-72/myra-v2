import structlog
from pathlib import Path
from app.config import settings
import mss
import mss.tools

logger = structlog.get_logger(__name__)

class VisionTools:
    def __init__(self):
        self.workspace_root = Path(settings.workspace_dir).resolve()
        
    def take_screenshot(self, output_filename: str = "screenshot.png") -> str:
        """
        Captures the primary monitor on-demand and saves it to the workspace.
        """
        try:
            clean_path = output_filename.lstrip("/").lstrip("\\")
            target_path = (self.workspace_root / clean_path).resolve()
            
            with mss.MSS() as sct:
                # Capture the primary monitor
                monitor = sct.monitors[1] # 0 is all monitors, 1 is primary
                sct_img = sct.grab(monitor)
                
                # Save it
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(target_path))
                
            logger.info("screenshot_captured", path=str(target_path))
            # The Assistant could theoretically load this image into its prompt buffer
            # to gain multimodal sight.
            return f"Screenshot successfully saved to {output_filename}. You can now analyze it."
            
        except Exception as e:
            logger.error("screenshot_failed", error=str(e))
            return f"Failed to take screenshot: {str(e)}"
