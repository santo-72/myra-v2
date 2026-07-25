import structlog
import psutil

logger = structlog.get_logger(__name__)

class PowerManager:
    """Thermal & Power Efficiency Scaling"""
    def __init__(self):
        self.is_throttling = False

    def check_power_state(self):
        battery = psutil.sensors_battery()
        if battery:
            logger.info(f"Battery: {battery.percent}% | Plugged In: {battery.power_plugged}")
            if not battery.power_plugged and battery.percent < 20:
                logger.warning("Low battery detected. Entering power-saving mode.")
                self.is_throttling = True
            else:
                self.is_throttling = False
        else:
            logger.debug("No battery detected (likely desktop).")

    def should_offload_heavy_tasks(self) -> bool:
        """Returns True if the system is on battery or thermal throttling."""
        self.check_power_state()
        return self.is_throttling
