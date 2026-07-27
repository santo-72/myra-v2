from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger(__name__)

class BaseMessagingAdapter(ABC):
    """
    Abstract base class defining the async contract for messaging adapters (web and native).
    """
    @abstractmethod
    async def open(self) -> bool:
        pass

    @abstractmethod
    async def find_contact_by_name(self, name: str) -> bool:
        pass

    @abstractmethod
    async def find_contact_by_number(self, number: str) -> bool:
        pass

    @abstractmethod
    async def type_message(self, message: str) -> bool:
        pass

    @abstractmethod
    async def send(self) -> bool:
        pass

    @abstractmethod
    async def confirm_sent(self) -> bool:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass
