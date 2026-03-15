__version__ = "0.2.0"

from ruleshield.cache import CacheManager
from ruleshield.config import Settings, load_settings
from ruleshield.extractor import PromptExtractor, RuleExtractor
from ruleshield.hermes_bridge import HermesBridge, trim_prompt
from ruleshield.metrics import MetricsCollector, MetricsDashboard
from ruleshield.router import ComplexityClassifier, SmartRouter
from ruleshield.rules import RuleEngine
from ruleshield.sdk import AsyncOpenAI, OpenAI

__all__ = [
    "AsyncOpenAI",
    "CacheManager",
    "ComplexityClassifier",
    "HermesBridge",
    "MetricsCollector",
    "MetricsDashboard",
    "OpenAI",
    "PromptExtractor",
    "RuleEngine",
    "RuleExtractor",
    "Settings",
    "SmartRouter",
    "load_settings",
    "trim_prompt",
]
