"""
Post Generator - main AI content generation engine.
Orchestrates Claude API, prompts, and SEO optimization.
"""

import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent
from app.models.post import Post
from app.ai.claude_client import get_claude_client
from app.ai.prompts import (
    build_system_prompt,
    build_post_generation_prompt,
    build_meta_title_prompt,
    build_meta_description_prompt,
    build_keywords_extraction_prompt,
)

logger = logging.getLogger(__name__)


class PostGenerator:
    """AI-powered blog post generator."""

    def __init__(self):
        """Initialize post generator."""
        self.claude = get_claude_client()

    async def generate_post(
        self,
        agent: Agent,
        topic: Optional[str] = None,
        keyword: Optional[str] = None,
        sources_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete blog post with SEO metadata.

        Args:
            agent: Agent with configuration (expertise, persona, tone)
            topic: Optional topic override (uses agent default if None)
            keyword: Optional target keyword
            sources_content: Optional source content to base post on

        Returns:
            Dictionary with post data:
            {
                "title": str,
                "content": str,
                "meta_title": str,
                "meta_description": str,
                "keywords": list[str],
                "tokens_used": int,
                "word_count": int,
                "generation_prompt": str
            }
        """
        try:
            logger.info(f"Generating post for agent {agent.name} (ID: {agent.id})")

            # Step 1: Build system prompt based on agent config
            system_prompt = build_system_prompt(
                expertise=agent.expertise,
                persona=agent.persona,
                tone=agent.tone,
            )

            # Step 2: Build generation prompt
            if not topic:
                topic = f"Najnowsze trendy w {agent.expertise}"

            generation_prompt = build_post_generation_prompt(
                topic=topic,
                keyword=keyword,
                length=agent.post_length,
                sources_content=sources_content,
            )

            # Step 3: Generate main content
            logger.info("Generating main content...")
            content, tokens_content = await self.claude.generate_text(
                prompt=generation_prompt,
                system_prompt=system_prompt,
            )

            if not content:
                raise ValueError("Generated content is empty")

            # Extract title from content (first # heading)
            title = self._extract_title(content)

            # Step 4: Generate meta title
            logger.info("Generating meta title...")
            meta_title_prompt = build_meta_title_prompt(content, keyword)
            meta_title, tokens_meta_title = await self.claude.generate_text(
                prompt=meta_title_prompt,
            )
            meta_title = meta_title.strip()[:70]  # Ensure max 70 chars

            # Step 5: Generate meta description
            logger.info("Generating meta description...")
            meta_desc_prompt = build_meta_description_prompt(content, keyword)
            meta_description, tokens_meta_desc = await self.claude.generate_text(
                prompt=meta_desc_prompt,
            )
            meta_description = meta_description.strip()[:160]  # Ensure max 160 chars

            # Step 6: Extract keywords
            logger.info("Extracting keywords...")
            keywords_prompt = build_keywords_extraction_prompt(content)
            keywords_json, tokens_keywords = await self.claude.generate_text(
                prompt=keywords_prompt,
            )

            # Parse keywords JSON
            try:
                keywords = json.loads(keywords_json.strip())
                if not isinstance(keywords, list):
                    keywords = []
            except json.JSONDecodeError:
                logger.warning("Failed to parse keywords JSON, using empty list")
                keywords = []

            # Calculate total tokens and word count
            total_tokens = (
                tokens_content +
                tokens_meta_title +
                tokens_meta_desc +
                tokens_keywords
            )
            word_count = len(content.split())

            logger.info(f"Post generated successfully: {word_count} words, {total_tokens} tokens")

            return {
                "title": title,
                "content": content,
                "meta_title": meta_title,
                "meta_description": meta_description,
                "keywords": keywords,
                "tokens_used": total_tokens,
                "word_count": word_count,
                "generation_prompt": generation_prompt[:1000],  # Store first 1000 chars
            }

        except Exception as e:
            logger.error(f"Error generating post: {e}", exc_info=True)
            raise

    def _extract_title(self, content: str) -> str:
        """
        Extract title from HTML or markdown content.

        Args:
            content: HTML or Markdown content

        Returns:
            Extracted title or "Untitled Post"
        """
        import re

        # Try HTML h1 or h2 first
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content, re.IGNORECASE)
        if h1_match:
            return h1_match.group(1).strip()

        h2_match = re.search(r'<h2[^>]*>([^<]+)</h2>', content, re.IGNORECASE)
        if h2_match:
            return h2_match.group(1).strip()

        # Fallback to Markdown
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            elif line.startswith("## "):
                return line[3:].strip()

        # Last fallback: use first non-empty text line
        for line in lines:
            line = line.strip()
            # Skip HTML tags
            clean_line = re.sub(r'<[^>]+>', '', line).strip()
            if clean_line and len(clean_line) > 10:
                return clean_line[:100]  # Max 100 chars

        return "Untitled Post"


# Global instance
_post_generator: Optional[PostGenerator] = None


def get_post_generator() -> PostGenerator:
    """Get global post generator instance."""
    global _post_generator
    if _post_generator is None:
        _post_generator = PostGenerator()
    return _post_generator
