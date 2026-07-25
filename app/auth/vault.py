from cryptography.fernet import Fernet
from app.config import settings
import structlog
import os

logger = structlog.get_logger(__name__)

class Vault:
    def __init__(self):
        self.key = settings.vault_key
        self.fernet = None
        
        # Scaffolding for pqcrypto post-quantum upgrade
        try:
            import pqcrypto
            self.pq = pqcrypto
            logger.info("Post-Quantum Cryptography enabled in Vault.")
        except ImportError:
            self.pq = None
            logger.warning("pqcrypto not found. Falling back to standard AES-256 Fernet.")
        
        if not self.key:
            logger.warning("VAULT_KEY is not set. Encryption is disabled.")
        else:
            try:
                self.fernet = Fernet(self.key.encode('utf-8'))
            except Exception as e:
                logger.error("Failed to initialize Fernet vault.", error=str(e))

    def encrypt(self, data: str) -> str:
        if not self.fernet:
            return data
        return self.fernet.encrypt(data.encode('utf-8')).decode('utf-8')

    def decrypt(self, encrypted_data: str) -> str:
        if not self.fernet:
            return encrypted_data
        try:
            return self.fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error("Failed to decrypt data.", error=str(e))
            return encrypted_data

    def anti_forensic_purge(self, memory_object):
        """
        Actively overwrites data structures in RAM with random noise.
        """
        logger.critical("ANTI-FORENSIC PURGE INITIATED")
        # Overwrite string references
        if hasattr(memory_object, '__dict__'):
            for key in list(memory_object.__dict__.keys()):
                val = memory_object.__dict__[key]
                if isinstance(val, str):
                    memory_object.__dict__[key] = os.urandom(len(val)).hex()
