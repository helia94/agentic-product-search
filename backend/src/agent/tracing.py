"""
OpenTelemetry tracing configuration for FastAPI application.
Replaces custom web tracer with production-ready Jaeger tracing.
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource


def configure_tracing(app, service_name: str = "product-search-api"):
    """
    Configure OpenTelemetry tracing for FastAPI application.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service for tracing
    """
    
    try:
        # Configure resource with service information
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
        })
        
        # Set up tracer provider
        trace.set_tracer_provider(TracerProvider(resource=resource))
        tracer_provider = trace.get_tracer_provider()
        
        # Only configure OTLP exporter if Jaeger endpoint is available
        jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://localhost:4317")
        
        # Test if Jaeger is available (optional - only if endpoint is configured)
        try:
            if jaeger_endpoint != "http://localhost:4317" or os.getenv("JAEGER_ENABLED", "false").lower() == "true":
                # Configure OTLP exporter to send traces to Jaeger
                otlp_exporter = OTLPSpanExporter(
                    endpoint=jaeger_endpoint,
                    insecure=True
                )
                
                # Add span processor
                span_processor = BatchSpanProcessor(otlp_exporter)
                tracer_provider.add_span_processor(span_processor)
                print(f"[TRACING] OTLP exporter configured for Jaeger: {jaeger_endpoint}")
            else:
                print(f"[TRACING] Jaeger not configured - traces will be collected but not exported")
                print(f"[TRACING] To enable Jaeger export, start Jaeger and set JAEGER_ENABLED=true")
                
        except Exception as e:
            print(f"[TRACING] Warning: Could not configure OTLP exporter: {e}")
            print(f"[TRACING] Continuing with in-memory tracing only")
        
        # Auto-instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        
        print(f"[TRACING] OpenTelemetry configured for service: {service_name}")
        
        return trace.get_tracer(__name__)
        
    except Exception as e:
        print(f"[TRACING] Error configuring OpenTelemetry: {e}")
        print(f"[TRACING] Continuing without distributed tracing")
        # Return a no-op tracer
        return trace.get_tracer(__name__)


def get_tracer():
    """Get the current tracer instance."""
    return trace.get_tracer(__name__)


def trace_function(operation_name: str):
    """
    Decorator to trace function execution.
    
    Usage:
        @trace_function("my_operation")
        def my_function():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def add_span_attribute(key: str, value):
    """Add attribute to current active span."""
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute(key, value)


def add_span_event(name: str, attributes=None):
    """Add event to current active span."""
    current_span = trace.get_current_span()
    if current_span:
        current_span.add_event(name, attributes or {})