"""
Adapter factory for creating source and publisher adapters.
"""

from typing import Dict, Any
from app.adapters.base import BaseSourceAdapter, BasePublisherAdapter
from app.adapters.sources.rss_adapter import RSSAdapter
from app.adapters.publishers.wordpress_adapter import WordPressAdapter
from app.adapters.publishers.webhook_adapter import WebhookAdapter


# Registry of available adapters
SOURCE_ADAPTERS = {
    "rss": RSSAdapter,
    # Add more as implemented:
    # "scraper": ScraperAdapter,
    # "search": SearchAdapter,
}

PUBLISHER_ADAPTERS = {
    "wordpress": WordPressAdapter,
    "webhook": WebhookAdapter,
    # Add more as implemented:
    # "ghost": GhostAdapter,
    # "medium": MediumAdapter,
}


def create_source_adapter(adapter_type: str, config: Dict[str, Any]) -> BaseSourceAdapter:
    """
    Create source adapter instance.

    Args:
        adapter_type: Type of adapter (rss, scraper, search)
        config: Adapter configuration

    Returns:
        Source adapter instance

    Raises:
        ValueError: If adapter type is not supported
    """
    adapter_class = SOURCE_ADAPTERS.get(adapter_type.lower())
    if not adapter_class:
        raise ValueError(
            f"Unknown source adapter type: {adapter_type}. "
            f"Available types: {list(SOURCE_ADAPTERS.keys())}"
        )

    return adapter_class(config)


def create_publisher_adapter(adapter_type: str, config: Dict[str, Any]) -> BasePublisherAdapter:
    """
    Create publisher adapter instance.

    Args:
        adapter_type: Type of adapter (wordpress, webhook, ghost)
        config: Adapter configuration

    Returns:
        Publisher adapter instance

    Raises:
        ValueError: If adapter type is not supported
    """
    adapter_class = PUBLISHER_ADAPTERS.get(adapter_type.lower())
    if not adapter_class:
        raise ValueError(
            f"Unknown publisher adapter type: {adapter_type}. "
            f"Available types: {list(PUBLISHER_ADAPTERS.keys())}"
        )

    return adapter_class(config)


__all__ = [
    "BaseSourceAdapter",
    "BasePublisherAdapter",
    "create_source_adapter",
    "create_publisher_adapter",
    "SOURCE_ADAPTERS",
    "PUBLISHER_ADAPTERS",
]
