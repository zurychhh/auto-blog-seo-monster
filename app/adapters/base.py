"""
Base adapter classes for sources and publishers.
Defines interfaces and common functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SourceContent:
    """Content fetched from a source."""
    title: str
    content: str
    url: Optional[str] = None
    published_at: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PublishResult:
    """Result of publishing a post."""
    success: bool
    published_url: Optional[str] = None
    published_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseSourceAdapter(ABC):
    """Base class for all source adapters."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize source adapter.

        Args:
            config: Adapter configuration (from Source.config)
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def fetch(self) -> List[SourceContent]:
        """
        Fetch content from the source.

        Returns:
            List of SourceContent objects

        Raises:
            Exception: If fetch fails
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to the source.

        Returns:
            Dictionary with test results:
            {
                "success": bool,
                "message": str,
                "items_found": int (optional),
                "error": str (optional)
            }
        """
        pass

    def _validate_config(self, required_fields: List[str]) -> None:
        """
        Validate that required config fields are present.

        Args:
            required_fields: List of required field names

        Raises:
            ValueError: If required field is missing
        """
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")


class BasePublisherAdapter(ABC):
    """Base class for all publisher adapters."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize publisher adapter.

        Args:
            config: Adapter configuration (from Publisher.config)
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def publish(
        self,
        title: str,
        content: str,
        excerpt: Optional[str] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        featured_image_url: Optional[str] = None,
        status: str = "publish",
        **kwargs
    ) -> PublishResult:
        """
        Publish post to the platform.

        Args:
            title: Post title
            content: Post content (HTML or Markdown)
            excerpt: Post excerpt
            meta_title: SEO meta title
            meta_description: SEO meta description
            keywords: List of keywords/tags
            featured_image_url: URL to featured image
            status: Post status (publish, draft, etc.)
            **kwargs: Additional platform-specific parameters

        Returns:
            PublishResult with publication details

        Raises:
            Exception: If publication fails
        """
        pass

    @abstractmethod
    async def update(
        self,
        post_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> PublishResult:
        """
        Update existing post.

        Args:
            post_id: Platform-specific post ID
            title: New title (optional)
            content: New content (optional)
            **kwargs: Additional fields to update

        Returns:
            PublishResult with update details

        Raises:
            Exception: If update fails
        """
        pass

    @abstractmethod
    async def delete(self, post_id: str) -> PublishResult:
        """
        Delete post from platform.

        Args:
            post_id: Platform-specific post ID

        Returns:
            PublishResult with deletion status

        Raises:
            Exception: If deletion fails
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to the platform.

        Returns:
            Dictionary with test results:
            {
                "success": bool,
                "message": str,
                "platform_info": dict (optional),
                "error": str (optional)
            }
        """
        pass

    def _validate_config(self, required_fields: List[str]) -> None:
        """
        Validate that required config fields are present.

        Args:
            required_fields: List of required field names

        Raises:
            ValueError: If required field is missing
        """
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
