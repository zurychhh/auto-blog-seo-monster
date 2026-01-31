"""
RSS/Atom feed adapter for fetching blog content.
Supports RSS 2.0, RSS 1.0, and Atom feeds.
"""

import feedparser
from typing import List, Dict, Any
from datetime import datetime
from app.adapters.base import BaseSourceAdapter, SourceContent


class RSSAdapter(BaseSourceAdapter):
    """
    Adapter for fetching content from RSS/Atom feeds.

    Config schema:
    {
        "feed_url": str,              # Required: RSS/Atom feed URL
        "max_items": int,             # Optional: Max items to fetch (default: 10)
        "include_content": bool,      # Optional: Include full content (default: True)
        "include_summary": bool,      # Optional: Include summary/excerpt (default: True)
    }
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._validate_config(["feed_url"])
        self.max_items = self.config.get("max_items", 10)
        self.include_content = self.config.get("include_content", True)
        self.include_summary = self.config.get("include_summary", True)

    async def fetch(self) -> List[SourceContent]:
        """
        Fetch entries from RSS/Atom feed.

        Returns:
            List of SourceContent objects

        Raises:
            Exception: If feed parsing fails
        """
        try:
            feed_url = self.config["feed_url"]
            self.logger.info(f"Fetching RSS feed: {feed_url}")

            # Parse feed (feedparser is sync, but fast)
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                # bozo=1 means malformed, but might still have entries
                raise Exception(f"Failed to parse feed: {feed.bozo_exception}")

            self.logger.info(f"Found {len(feed.entries)} entries in feed")

            # Convert entries to SourceContent
            contents = []
            for entry in feed.entries[:self.max_items]:
                content = self._parse_entry(entry)
                if content:
                    contents.append(content)

            self.logger.info(f"Successfully parsed {len(contents)} entries")
            return contents

        except Exception as e:
            self.logger.error(f"Error fetching RSS feed: {e}", exc_info=True)
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test RSS feed connection.

        Returns:
            Test results with feed info
        """
        try:
            feed_url = self.config["feed_url"]
            self.logger.info(f"Testing RSS feed: {feed_url}")

            # Try to parse feed
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                return {
                    "success": False,
                    "message": f"Failed to parse feed",
                    "error": str(feed.bozo_exception)
                }

            # Extract feed info
            feed_info = {
                "title": feed.feed.get("title", "Unknown"),
                "link": feed.feed.get("link", ""),
                "description": feed.feed.get("subtitle", feed.feed.get("description", "")),
                "items_found": len(feed.entries),
                "feed_type": feed.version or "unknown"
            }

            return {
                "success": True,
                "message": f"Successfully connected to feed: {feed_info['title']}",
                "items_found": len(feed.entries),
                "feed_info": feed_info
            }

        except Exception as e:
            self.logger.error(f"Error testing RSS feed: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Connection test failed",
                "error": str(e)
            }

    def _parse_entry(self, entry) -> SourceContent:
        """
        Parse feedparser entry to SourceContent.

        Args:
            entry: feedparser entry object

        Returns:
            SourceContent or None if parsing fails
        """
        try:
            # Extract title
            title = entry.get("title", "Untitled")

            # Extract content (try content, then summary, then description)
            content = ""
            if self.include_content:
                if hasattr(entry, "content") and entry.content:
                    # Atom feeds have content
                    content = entry.content[0].value
                elif hasattr(entry, "summary_detail") and entry.summary_detail:
                    content = entry.summary_detail.value
                elif hasattr(entry, "summary"):
                    content = entry.summary
                elif hasattr(entry, "description"):
                    content = entry.description

            # Extract URL
            url = entry.get("link", None)

            # Extract publish date
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6]).isoformat()
                except:
                    pass
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                try:
                    published_at = datetime(*entry.updated_parsed[:6]).isoformat()
                except:
                    pass

            # Extract author
            author = entry.get("author", None)

            # Extract tags
            tags = []
            if hasattr(entry, "tags"):
                tags = [tag.term for tag in entry.tags if hasattr(tag, "term")]

            # Metadata
            metadata = {
                "feed_id": entry.get("id", url),
                "feed_source": self.config["feed_url"],
            }

            return SourceContent(
                title=title,
                content=content,
                url=url,
                published_at=published_at,
                author=author,
                tags=tags,
                metadata=metadata
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse entry: {e}")
            return None
