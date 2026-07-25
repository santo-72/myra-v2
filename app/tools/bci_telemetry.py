import structlog
import threading
import time

logger = structlog.get_logger(__name__)

class BCITelemetry:
    """Reads focus/fatigue metrics from Brain-Computer Interface (EEG)"""
    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.is_reading = False
        self.current_focus_level = 0.5 # 0.0 to 1.0
        
        if not self.mock_mode:
            try:
                from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
                self.board = None # setup board
                logger.info("BCITelemetry initialized with BrainFlow")
            except ImportError:
                logger.error("BrainFlow not found. Falling back to mock mode.")
                self.mock_mode = True
        else:
            logger.info("BCITelemetry initialized in MOCK mode")

    def start_reading(self):
        if not self.is_reading:
            self.is_reading = True
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            logger.info("BCITelemetry started reading EEG data.")

    def stop_reading(self):
        self.is_reading = False
        logger.info("BCITelemetry stopped reading EEG data.")

    def _read_loop(self):
        import random
        while self.is_reading:
            if self.mock_mode:
                # Simulate focus level floating between 0.2 and 0.8
                self.current_focus_level = max(0.0, min(1.0, self.current_focus_level + random.uniform(-0.1, 0.1))) # nosec B311
            else:
                # Actual brainflow read
                pass
            time.sleep(1)
