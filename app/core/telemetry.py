import structlog
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
except ImportError:
    pass

logger = structlog.get_logger(__name__)

class TelemetryManager:
    """Structured Telemetry and OpenTelemetry integration"""
    def __init__(self):
        self.tracer = None
        try:
            provider = TracerProvider()
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            self.tracer = trace.get_tracer(__name__)
            logger.info("OpenTelemetry configured successfully.")
        except Exception as e:
            logger.error("Failed to configure OpenTelemetry.", error=str(e))
            
    def get_tracer(self):
        return self.tracer
