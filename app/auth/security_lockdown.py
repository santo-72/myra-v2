import structlog
import os
from typing import Callable

logger = structlog.get_logger(__name__)

class SecurityLockdown:
    """Handles emergency panic and decoy modes for M.Y.R.A"""
    def __init__(self):
        logger.info("SecurityLockdown protocol ready")
        
    def trigger_panic(self, purge_callback: Callable = None):
        """
        Triggers panic mode: lock databases, purge keys in memory.
        """
        logger.critical("PANIC MODE TRIGGERED. Purging sensitive state.")
        if purge_callback:
            try:
                purge_callback()
            except Exception as e:
                logger.error("Purge callback failed", error=str(e))
        
        # Wipe env vars in memory
        if "VAULT_KEY" in os.environ:
            del os.environ["VAULT_KEY"]
            
    def engage_decoy_mode(self) -> str:
        """
        Triggers decoy mode: switches workspace to a harmless sandbox.
        """
        logger.warning("DECOY MODE ENGAGED.")
        decoy_path = os.path.join(os.getcwd(), "decoy_sandbox")
        if not os.path.exists(decoy_path):
            os.makedirs(decoy_path)
            
        # Write dummy files
        with open(os.path.join(decoy_path, "notes.txt"), "w") as f:
            f.write("Nothing to see here. Just a normal workspace.")
            
        return decoy_path
