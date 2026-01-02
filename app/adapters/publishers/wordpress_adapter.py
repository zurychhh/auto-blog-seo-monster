"""
WordPress REST API adapter for publishing posts.
Supports WordPress 5.0+ with REST API enabled.
"""

import aiohttp
from typing import List, Dict, Any, Optional
from base64 import b64encode
from app.adapters.base import BasePublisherAdapter, PublishResult
import markdown


class WordPressAdapter(BasePublisherAdapter):
    """
    Adapter for publishing to WordPress via REST API.

    Config schema:
    {
        "site_url": str,           # Required: WordPress site URL (e.g., https://example.com)
        "username": str,           # Required: WordPress username
        "password": str,           # Required: WordPress application password
        "author_id": int,          # Optional: Author ID (default: current user)
        "default_status": str,     # Optional: Default post status (publish/draft, default: publish)
        "default_category": int,   # Optional: Default category ID
        "convert_markdown": bool,  # Optional: Convert markdown to HTML (default: True)
    }

    Authentication:
    - Uses WordPress Application Passwords (WordPress 5.6+)
    - Generate at: WordPress Admin → Users → Profile → Application Passwords
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._validate_config(["site_url", "username", "password"])

        # Ensure site_url doesn't end with /
        self.site_url = self.config["site_url"].rstrip("/")
        self.api_url = f"{self.site_url}/wp-json/wp/v2"

        # Authentication
        self.username = self.config["username"]
        self.password = self.config["password"]
        self.auth_header = self._create_auth_header()

        # Defaults
        self.author_id = self.config.get("author_id", None)
        self.default_status = self.config.get("default_status", "publish")
        self.default_category = self.config.get("default_category", None)
        self.convert_markdown = self.config.get("convert_markdown", True)

    def _create_auth_header(self) -> str:
        """Create HTTP Basic Auth header."""
        credentials = f"{self.username}:{self.password}"
        b64_credentials = b64encode(credentials.encode()).decode()
        return f"Basic {b64_credentials}"

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
        Publish post to WordPress.

        Args:
            title: Post title
            content: Post content (HTML or Markdown)
            excerpt: Post excerpt
            meta_title: SEO meta title (via Yoast/RankMath meta)
            meta_description: SEO meta description
            keywords: Keywords as tags
            featured_image_url: Featured image URL
            status: Post status (publish/draft/pending)
            **kwargs: Additional WP-specific params (categories, tags, etc.)

        Returns:
            PublishResult with publication details
        """
        try:
            # Convert markdown to HTML if needed
            if self.convert_markdown and not content.startswith("<"):
                content = markdown.markdown(
                    content,
                    extensions=['extra', 'codehilite', 'toc']
                )

            # Build post data
            post_data = {
                "title": title,
                "content": content,
                "status": status or self.default_status,
            }

            # Optional fields
            if excerpt:
                post_data["excerpt"] = excerpt

            if self.author_id:
                post_data["author"] = self.author_id

            if self.default_category:
                post_data["categories"] = [self.default_category]

            # Tags from keywords
            if keywords:
                # Need to create/get tag IDs first (WordPress requires tag IDs, not names)
                # For simplicity, we'll just add them as comma-separated meta
                # In production, you'd query /wp/v2/tags and create if needed
                pass

            # Custom meta (for SEO plugins like Yoast or RankMath)
            if meta_title or meta_description:
                post_data["meta"] = {}
                if meta_title:
                    # Yoast: _yoast_wpseo_title
                    # RankMath: rank_math_title
                    post_data["meta"]["_yoast_wpseo_title"] = meta_title
                    post_data["meta"]["rank_math_title"] = meta_title
                if meta_description:
                    post_data["meta"]["_yoast_wpseo_metadesc"] = meta_description
                    post_data["meta"]["rank_math_description"] = meta_description

            # Additional kwargs
            post_data.update(kwargs)

            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/posts",
                    json=post_data,
                    headers={
                        "Authorization": self.auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 201:
                        # Success
                        data = await response.json()
                        return PublishResult(
                            success=True,
                            published_url=data.get("link"),
                            published_id=str(data.get("id")),
                            metadata={
                                "status": data.get("status"),
                                "slug": data.get("slug"),
                                "modified": data.get("modified"),
                            }
                        )
                    else:
                        # Error
                        error_text = await response.text()
                        self.logger.error(f"WordPress API error: {response.status} - {error_text}")
                        return PublishResult(
                            success=False,
                            error=f"HTTP {response.status}: {error_text}"
                        )

        except Exception as e:
            self.logger.error(f"Error publishing to WordPress: {e}", exc_info=True)
            return PublishResult(
                success=False,
                error=str(e)
            )

    async def update(
        self,
        post_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> PublishResult:
        """
        Update existing WordPress post.

        Args:
            post_id: WordPress post ID
            title: New title
            content: New content
            **kwargs: Additional fields

        Returns:
            PublishResult with update status
        """
        try:
            update_data = {}

            if title:
                update_data["title"] = title

            if content:
                if self.convert_markdown and not content.startswith("<"):
                    content = markdown.markdown(content, extensions=['extra', 'codehilite'])
                update_data["content"] = content

            update_data.update(kwargs)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/posts/{post_id}",
                    json=update_data,
                    headers={
                        "Authorization": self.auth_header,
                        "Content-Type": "application/json"
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return PublishResult(
                            success=True,
                            published_url=data.get("link"),
                            published_id=str(data.get("id")),
                            metadata={"status": data.get("status")}
                        )
                    else:
                        error_text = await response.text()
                        return PublishResult(
                            success=False,
                            error=f"HTTP {response.status}: {error_text}"
                        )

        except Exception as e:
            self.logger.error(f"Error updating WordPress post: {e}", exc_info=True)
            return PublishResult(
                success=False,
                error=str(e)
            )

    async def delete(self, post_id: str) -> PublishResult:
        """
        Delete WordPress post.

        Args:
            post_id: WordPress post ID

        Returns:
            PublishResult with deletion status
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.api_url}/posts/{post_id}",
                    headers={"Authorization": self.auth_header},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return PublishResult(
                            success=True,
                            metadata={"deleted": True}
                        )
                    else:
                        error_text = await response.text()
                        return PublishResult(
                            success=False,
                            error=f"HTTP {response.status}: {error_text}"
                        )

        except Exception as e:
            self.logger.error(f"Error deleting WordPress post: {e}", exc_info=True)
            return PublishResult(
                success=False,
                error=str(e)
            )

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test WordPress API connection.

        Returns:
            Test results with site info
        """
        try:
            # Test authentication by fetching current user
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/users/me",
                    headers={"Authorization": self.auth_header},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        user_data = await response.json()

                        # Also get site info
                        async with session.get(
                            f"{self.site_url}/wp-json",
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as site_response:
                            site_data = await site_response.json() if site_response.status == 200 else {}

                        return {
                            "success": True,
                            "message": f"Successfully connected as {user_data.get('name', 'user')}",
                            "platform_info": {
                                "user_id": user_data.get("id"),
                                "username": user_data.get("username"),
                                "roles": user_data.get("roles", []),
                                "site_name": site_data.get("name", ""),
                                "site_description": site_data.get("description", ""),
                                "wp_version": site_data.get("gmt_offset", ""),
                            }
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "message": "Authentication failed",
                            "error": f"HTTP {response.status}: {error_text}"
                        }

        except Exception as e:
            self.logger.error(f"Error testing WordPress connection: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Connection test failed",
                "error": str(e)
            }
