"""
SEO Service - SEO optimization utilities.
Readability scoring, schema markup, keyword analysis.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import textstat
from slugify import slugify as python_slugify
import logging

logger = logging.getLogger(__name__)


class SEOService:
    """SEO optimization service."""

    @staticmethod
    def calculate_readability_score(content: str) -> float:
        """
        Calculate Flesch Reading Ease score.

        Score interpretation:
        - 90-100: Very Easy (5th grade)
        - 80-90: Easy (6th grade)
        - 70-80: Fairly Easy (7th grade)
        - 60-70: Standard (8th-9th grade)
        - 50-60: Fairly Difficult (10th-12th grade)
        - 30-50: Difficult (College)
        - 0-30: Very Confusing (College graduate)

        Args:
            content: Text content

        Returns:
            Readability score (0-100, higher is better)
        """
        try:
            # Remove markdown formatting for accurate measurement
            clean_text = SEOService._strip_markdown(content)

            if not clean_text:
                return 0.0

            # Calculate Flesch Reading Ease
            score = textstat.flesch_reading_ease(clean_text)

            # Ensure score is in valid range
            return max(0.0, min(100.0, score))

        except Exception as e:
            logger.error(f"Error calculating readability: {e}")
            return 50.0  # Return neutral score on error

    @staticmethod
    def calculate_keyword_density(content: str, keywords: List[str]) -> Dict[str, float]:
        """
        Calculate keyword density percentages.

        Optimal density: 1-2% for main keyword, 0.5-1% for related keywords.

        Args:
            content: Text content
            keywords: List of keywords to analyze

        Returns:
            Dictionary mapping keyword -> density percentage
        """
        try:
            clean_text = SEOService._strip_markdown(content).lower()
            total_words = len(clean_text.split())

            if total_words == 0:
                return {}

            densities = {}
            for keyword in keywords:
                keyword_lower = keyword.lower()
                count = clean_text.count(keyword_lower)
                density = (count / total_words) * 100
                densities[keyword] = round(density, 2)

            return densities

        except Exception as e:
            logger.error(f"Error calculating keyword density: {e}")
            return {}

    @staticmethod
    def generate_schema_markup(
        post_title: str,
        post_content: str,
        published_url: Optional[str] = None,
        author_name: str = "Auto-Blog SEO Monster",
        published_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate Article schema markup (JSON-LD).

        Args:
            post_title: Post title
            post_content: Post content
            published_url: Published URL
            author_name: Author name
            published_at: Publication datetime

        Returns:
            Schema.org Article markup as dict
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": post_title[:110],  # Max 110 chars for Google
            "author": {
                "@type": "Person",
                "name": author_name
            },
        }

        if published_url:
            schema["url"] = published_url
            schema["mainEntityOfPage"] = {
                "@type": "WebPage",
                "@id": published_url
            }

        if published_at:
            schema["datePublished"] = published_at.isoformat()
            schema["dateModified"] = published_at.isoformat()

        # Extract excerpt for description
        excerpt = SEOService._extract_excerpt(post_content, max_length=200)
        if excerpt:
            schema["description"] = excerpt

        # Word count
        word_count = len(post_content.split())
        schema["wordCount"] = word_count

        return schema

    @staticmethod
    def generate_slug(title: str) -> str:
        """
        Generate URL-friendly slug from title.

        Args:
            title: Post title

        Returns:
            URL slug
        """
        return python_slugify(title, max_length=100)

    @staticmethod
    def generate_og_tags(
        title: str,
        description: str,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate Open Graph meta tags.

        Args:
            title: Page title
            description: Page description
            url: Canonical URL
            image_url: OG image URL

        Returns:
            Dictionary of OG tags
        """
        tags = {
            "og:title": title[:70],
            "og:description": description[:160],
            "og:type": "article",
        }

        if url:
            tags["og:url"] = url

        if image_url:
            tags["og:image"] = image_url

        # Twitter Card tags
        tags["twitter:card"] = "summary_large_image"
        tags["twitter:title"] = title[:70]
        tags["twitter:description"] = description[:160]

        if image_url:
            tags["twitter:image"] = image_url

        return tags

    @staticmethod
    def _strip_markdown(content: str) -> str:
        """
        Remove markdown formatting from content.

        Args:
            content: Markdown content

        Returns:
            Plain text
        """
        # Remove code blocks
        content = re.sub(r'```[\s\S]*?```', '', content)

        # Remove inline code
        content = re.sub(r'`[^`]+`', '', content)

        # Remove links
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)

        # Remove images
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', content)

        # Remove bold/italic
        content = re.sub(r'[\*_]{1,2}([^\*_]+)[\*_]{1,2}', r'\1', content)

        # Remove headings
        content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)

        # Remove lists
        content = re.sub(r'^\s*[\-\*\+]\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*\d+\.\s+', '', content, flags=re.MULTILINE)

        # Remove horizontal rules
        content = re.sub(r'^[\-\*_]{3,}$', '', content, flags=re.MULTILINE)

        # Remove blockquotes
        content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)

        # Clean up whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    @staticmethod
    def _extract_excerpt(content: str, max_length: int = 200) -> str:
        """
        Extract excerpt from content.

        Args:
            content: Post content
            max_length: Maximum excerpt length

        Returns:
            Excerpt string
        """
        clean_text = SEOService._strip_markdown(content)
        sentences = re.split(r'[.!?]+', clean_text)

        excerpt = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(excerpt) + len(sentence) <= max_length:
                excerpt += sentence + ". "
            else:
                break

        return excerpt.strip()


# Global instance
_seo_service: Optional[SEOService] = None


def get_seo_service() -> SEOService:
    """Get global SEO service instance."""
    global _seo_service
    if _seo_service is None:
        _seo_service = SEOService()
    return _seo_service
