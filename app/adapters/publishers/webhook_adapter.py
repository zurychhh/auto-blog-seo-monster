"""
Webhook adapter for publishing to custom CMS/platforms.
Sends POST request with post data to configured webhook URL.
"""

import aiohttp
from typing import List, Dict, Any, Optional
from app.adapters.base import BasePublisherAdapter, PublishResult


class WebhookAdapter(BasePublisherAdapter):
    """
    Generic webhook adapter for custom integrations.

    Config schema:
    {
        "webhook_url": str,        # Required: Webhook endpoint URL
        "method": str,             # Optional: HTTP method (POST/PUT, default: POST)
        "headers": dict,           # Optional: Custom headers
        "auth_type": str,          # Optional: Authentication type (bearer/basic/api_key/none)
        "auth_token": str,         # Optional: Auth token/key
        "timeout": int,            # Optional: Request timeout in seconds (default: 30)
        "verify_ssl": bool,        # Optional: Verify SSL certificates (default: True)
    }

    Payload format sent to webhook:
    {
        "action": "publish" | "update" | "delete",
        "post_id": str (for update/delete),
        "title": str,
        "content": str,
        "excerpt": str,
        "meta_title": str,
        "meta_description": str,
        "keywords": list[str],
        "featured_image_url": str,
        "status": str,
        "metadata": dict  # Any additional kwargs
    }
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._validate_config(["webhook_url"])

        self.webhook_url = self.config["webhook_url"]
        self.method = self.config.get("method", "POST").upper()
        self.custom_headers = self.config.get("headers", {})
        self.auth_type = self.config.get("auth_type", "none")
        self.auth_token = self.config.get("auth_token", "")
        self.timeout = self.config.get("timeout", 30)
        self.verify_ssl = self.config.get("verify_ssl", True)

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            **self.custom_headers
        }

        # Add authentication
        if self.auth_type == "bearer" and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif self.auth_type == "api_key" and self.auth_token:
            headers["X-API-Key"] = self.auth_token
        elif self.auth_type == "basic" and self.auth_token:
            headers["Authorization"] = f"Basic {self.auth_token}"

        return headers

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
        Send post data to webhook.

        Args:
            title: Post title
            content: Post content
            excerpt: Post excerpt
            meta_title: SEO meta title
            meta_description: SEO meta description
            keywords: Keywords list
            featured_image_url: Featured image URL
            status: Post status
            **kwargs: Additional metadata

        Returns:
            PublishResult with webhook response
        """
        try:
            # Build payload
            payload = {
                "action": "publish",
                "title": title,
                "content": content,
                "excerpt": excerpt,
                "meta_title": meta_title,
                "meta_description": meta_description,
                "keywords": keywords or [],
                "featured_image_url": featured_image_url,
                "status": status,
                "metadata": kwargs
            }

            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    self.method,
                    self.webhook_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    response_data = await response.json() if response.content_type == "application/json" else {}
                    response_text = await response.text()

                    if 200 <= response.status < 300:
                        # Success
                        return PublishResult(
                            success=True,
                            published_url=response_data.get("url"),
                            published_id=response_data.get("id") or response_data.get("post_id"),
                            metadata={
                                "status_code": response.status,
                                "response": response_data or response_text[:500]
                            }
                        )
                    else:
                        # Error
                        self.logger.error(f"Webhook error: {response.status} - {response_text}")
                        return PublishResult(
                            success=False,
                            error=f"HTTP {response.status}: {response_text[:200]}"
                        )

        except Exception as e:
            self.logger.error(f"Error sending webhook: {e}", exc_info=True)
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
        Send update request to webhook.

        Args:
            post_id: Post ID to update
            title: New title
            content: New content
            **kwargs: Additional fields

        Returns:
            PublishResult with update status
        """
        try:
            payload = {
                "action": "update",
                "post_id": post_id,
                "title": title,
                "content": content,
                "metadata": kwargs
            }

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    self.method,
                    self.webhook_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    response_data = await response.json() if response.content_type == "application/json" else {}

                    if 200 <= response.status < 300:
                        return PublishResult(
                            success=True,
                            published_url=response_data.get("url"),
                            published_id=post_id,
                            metadata={"status_code": response.status}
                        )
                    else:
                        error_text = await response.text()
                        return PublishResult(
                            success=False,
                            error=f"HTTP {response.status}: {error_text[:200]}"
                        )

        except Exception as e:
            self.logger.error(f"Error updating via webhook: {e}", exc_info=True)
            return PublishResult(
                success=False,
                error=str(e)
            )

    async def delete(self, post_id: str) -> PublishResult:
        """
        Send delete request to webhook.

        Args:
            post_id: Post ID to delete

        Returns:
            PublishResult with deletion status
        """
        try:
            payload = {
                "action": "delete",
                "post_id": post_id
            }

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    self.method,
                    self.webhook_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if 200 <= response.status < 300:
                        return PublishResult(
                            success=True,
                            metadata={"deleted": True}
                        )
                    else:
                        error_text = await response.text()
                        return PublishResult(
                            success=False,
                            error=f"HTTP {response.status}: {error_text[:200]}"
                        )

        except Exception as e:
            self.logger.error(f"Error deleting via webhook: {e}", exc_info=True)
            return PublishResult(
                success=False,
                error=str(e)
            )

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test webhook connection with ping request.

        Returns:
            Test results
        """
        try:
            # Send test payload
            test_payload = {
                "action": "test",
                "message": "Connection test from Auto-Blog SEO Monster"
            }

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    self.method,
                    self.webhook_url,
                    json=test_payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=self.verify_ssl
                ) as response:
                    if 200 <= response.status < 300:
                        response_data = await response.json() if response.content_type == "application/json" else {}
                        return {
                            "success": True,
                            "message": "Webhook connection successful",
                            "platform_info": {
                                "status_code": response.status,
                                "response": response_data
                            }
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "message": "Webhook returned error",
                            "error": f"HTTP {response.status}: {error_text[:200]}"
                        }

        except Exception as e:
            self.logger.error(f"Error testing webhook: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Connection test failed",
                "error": str(e)
            }
