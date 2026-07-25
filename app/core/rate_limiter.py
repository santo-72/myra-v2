import structlog
import asyncio
try:
    from aiolimiter import AsyncLimiter
except ImportError:
    pass

logger = structlog.get_logger(__name__)

class RateLimiter:
    """Dynamic API Rate Limiter to prevent quota exhaustion"""
    def __init__(self, max_requests: int = 15, time_period: float = 60.0):
        # Default: 15 requests per minute
        try:
            self.limiter = AsyncLimiter(max_requests, time_period)
            logger.info(f"Rate Limiter configured: {max_requests} req / {time_period}s")
        except NameError:
            self.limiter = None
            logger.warning("aiolimiter not found. Rate limiting disabled.")

    async def wait(self):
        """Wait for budget before proceeding with an API call"""
        if self.limiter:
            await self.limiter.acquire()
            logger.debug("Rate limit budget acquired.")
        else:
            await asyncio.sleep(0) # Yield control briefly
