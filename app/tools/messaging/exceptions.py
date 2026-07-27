"""
Custom exceptions for automated messaging flows and native desktop adapter GUI interactions.
"""

class MessagingAdapterError(Exception):
    """Base exception for failures in automated messaging adapters (native or web)."""
    pass

class ContactSearchBoxNotFoundError(MessagingAdapterError):
    """Raised when the application's search box cannot be located or focused after retries."""
    pass

class ContactResultNotFoundError(MessagingAdapterError):
    """Raised when a specific contact cannot be found or activated in the search results after retries."""
    pass

class ComposeBoxNotFoundError(MessagingAdapterError):
    """Raised when the chat message compose text input area cannot be located after retries."""
    pass

class SendButtonNotFoundError(MessagingAdapterError):
    """Raised when the send button cannot be located or activated via Enter fallback after retries."""
    pass

class MessageSendVerificationError(MessagingAdapterError):
    """Raised when the message sent status indicator cannot be confirmed after transmission attempt."""
    pass
