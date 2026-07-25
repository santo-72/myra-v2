import structlog
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from app.config import settings
import io

logger = structlog.get_logger(__name__)

class DataAnalysisTools:
    def __init__(self):
        self.workspace_root = Path(settings.workspace_dir).resolve()
        
    def _safe_path(self, relative_path: str) -> Path:
        clean_path = relative_path.lstrip("/").lstrip("\\")
        target_path = (self.workspace_root / clean_path).resolve()
        try:
            target_path.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(f"Access Denied: Path '{relative_path}' is outside sandbox.")
        return target_path

    def analyze_csv_summary(self, file_path: str) -> str:
        """Loads a CSV and returns its info, head, and descriptive statistics."""
        try:
            safe_path = self._safe_path(file_path)
            if not safe_path.exists():
                return f"Error: File {file_path} not found."
                
            df = pd.read_csv(safe_path)
            
            # Capture df.info()
            buf = io.StringIO()
            df.info(buf=buf)
            info_str = buf.getvalue()
            
            # Capture stats
            desc_str = df.describe().to_string()
            
            # Head
            head_str = df.head(5).to_string()
            
            return f"--- INFO ---\n{info_str}\n\n--- STATS ---\n{desc_str}\n\n--- HEAD (5) ---\n{head_str}"
            
        except Exception as e:
            logger.error("csv_analysis_failed", error=str(e))
            return f"Analysis Failed: {str(e)}"

    def plot_basic_chart(self, file_path: str, x_column: str, y_column: str, chart_type: str, output_filename: str = "chart.png") -> str:
        """Plots a basic chart from a CSV and saves it to the workspace."""
        try:
            safe_input = self._safe_path(file_path)
            safe_output = self._safe_path(output_filename)
            
            df = pd.read_csv(safe_input)
            
            plt.figure(figsize=(10, 6))
            sns.set_theme(style="darkgrid")
            
            if chart_type.lower() == "bar":
                sns.barplot(data=df, x=x_column, y=y_column)
            elif chart_type.lower() == "line":
                sns.lineplot(data=df, x=x_column, y=y_column)
            elif chart_type.lower() == "scatter":
                sns.scatterplot(data=df, x=x_column, y=y_column)
            else:
                return f"Error: Unsupported chart type '{chart_type}'. Use bar, line, or scatter."
                
            plt.title(f"{y_column} vs {x_column}")
            plt.tight_layout()
            
            plt.savefig(safe_output)
            plt.close()
            
            logger.info("chart_plotted", output=str(safe_output))
            return f"Successfully generated chart and saved to {output_filename}"
            
        except Exception as e:
            logger.error("plot_failed", error=str(e))
            return f"Plotting Failed: {str(e)}"
