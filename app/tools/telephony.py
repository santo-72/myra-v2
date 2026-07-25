from twilio.rest import Client
import structlog
from app.config import settings

logger = structlog.get_logger(__name__)

class Telephony:
    """Handles sending SMS and making voice calls via Twilio"""
    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_phone_number
        
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Telephony (Twilio) client initialized")
            except Exception as e:
                logger.error("Failed to initialize Twilio client", error=str(e))
                self.client = None
        else:
            logger.warning("Twilio credentials not found in config. Telephony disabled.")
            self.client = None

    def send_sms(self, to_number: str, message: str) -> bool:
        if not self.client:
            logger.error("Cannot send SMS: Twilio client not initialized")
            return False
            
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            logger.info(f"SMS sent to {to_number}, SID: {msg.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}", error=str(e))
            return False

    def make_call(self, to_number: str, twiml_url: str) -> bool:
        if not self.client:
            logger.error("Cannot make call: Twilio client not initialized")
            return False
            
        try:
            call = self.client.calls.create(
                url=twiml_url,
                to=to_number,
                from_=self.from_number
            )
            logger.info(f"Call initiated to {to_number}, SID: {call.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to make call to {to_number}", error=str(e))
            return False
