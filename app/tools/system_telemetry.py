import psutil
import structlog
from typing import Dict, Any

logger = structlog.get_logger(__name__)

class SystemTelemetry:
    """Collects system hardware telemetry for M.Y.R.A"""
    def get_metrics(self) -> Dict[str, Any]:
        try:
            metrics = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "battery": None
            }
            if hasattr(psutil, "sensors_battery"):
                battery = psutil.sensors_battery()
                if battery:
                    metrics["battery"] = {
                        "percent": battery.percent,
                        "power_plugged": battery.power_plugged
                    }
            return metrics
        except Exception as e:
            logger.error("Failed to get system telemetry", error=str(e))
            return {}

    async def get_metrics_async(self) -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(self.get_metrics)
