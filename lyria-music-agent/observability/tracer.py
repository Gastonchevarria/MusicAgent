"""
OpenTelemetry tracer para spans de cada etapa del pipeline.
Exporta a stdout (desarrollo) — en producción apuntar a Jaeger/Grafana.
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)
trace.set_tracer_provider(provider)


def get_tracer():
    return trace.get_tracer("music-agent")
