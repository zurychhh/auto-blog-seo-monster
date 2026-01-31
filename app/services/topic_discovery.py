"""
Topic Discovery Service - Discover trending legal topics in Poland.

Sources:
- RSS feeds from Polish legal portals
- Google News Poland (legal category)
- AI-powered topic analysis
"""

import logging
import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Polish legal news RSS feeds
POLISH_LEGAL_RSS_FEEDS = [
    {
        "name": "Prawo.pl",
        "url": "https://www.prawo.pl/rss",
        "category": "prawo ogólne",
    },
    {
        "name": "Infor Prawo",
        "url": "https://www.infor.pl/prawo/rss.xml",
        "category": "prawo ogólne",
    },
    {
        "name": "Gazeta Prawna",
        "url": "https://www.gazetaprawna.pl/rss.xml",
        "category": "prawo biznesowe",
    },
    {
        "name": "Rzeczpospolita Prawo",
        "url": "https://www.rp.pl/rss/4652-prawo",
        "category": "prawo",
    },
    {
        "name": "Google News PL - Prawo",
        "url": "https://news.google.com/rss/search?q=prawo+polska+przepisy&hl=pl&gl=PL&ceid=PL:pl",
        "category": "aktualności prawne",
    },
    {
        "name": "Google News PL - Zmiany w prawie",
        "url": "https://news.google.com/rss/search?q=zmiany+w+prawie+2025&hl=pl&gl=PL&ceid=PL:pl",
        "category": "zmiany prawne",
    },
]

# Legal categories mapping
LEGAL_CATEGORIES = {
    "cywilne": ["umowa", "najem", "kupno", "sprzedaż", "odszkodowanie", "roszczenie"],
    "pracy": ["pracodawca", "pracownik", "urlop", "zwolnienie", "wynagrodzenie", "ZUS"],
    "konsumenckie": ["konsument", "reklamacja", "zwrot", "gwarancja", "sklep"],
    "rodzinne": ["alimenty", "rozwód", "opieka", "rodzina", "dziecko", "małżeństwo"],
    "spadkowe": ["spadek", "testament", "dziedziczenie", "zachowek", "notariusz"],
    "administracyjne": ["urząd", "decyzja", "odwołanie", "pozwolenie", "licencja"],
    "mieszkaniowe": ["mieszkanie", "lokal", "wspólnota", "czynsz", "eksmisja"],
}


@dataclass
class DiscoveredTopic:
    """Discovered topic from news sources."""
    title: str
    description: str
    source: str
    source_url: str
    category: str
    published_at: Optional[datetime]

    # Calculated scores
    relevance_score: float = 0.0
    freshness_score: float = 0.0
    seo_potential: float = 0.0

    # AI suggestions (filled later)
    suggested_keywords: List[str] = None
    suggested_title: str = None
    suggested_angle: str = None

    def __post_init__(self):
        if self.suggested_keywords is None:
            self.suggested_keywords = []


class TopicDiscoveryService:
    """Service for discovering trending legal topics in Poland."""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._already_covered_titles: set = set()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def discover_topics(
        self,
        categories: Optional[List[str]] = None,
        max_topics: int = 10,
        exclude_titles: Optional[List[str]] = None,
    ) -> List[DiscoveredTopic]:
        """
        Discover trending legal topics from multiple sources.

        Args:
            categories: Filter by legal categories (e.g., ["cywilne", "pracy"])
            max_topics: Maximum number of topics to return
            exclude_titles: Titles to exclude (already covered)

        Returns:
            List of discovered topics, sorted by relevance
        """
        if exclude_titles:
            self._already_covered_titles.update(exclude_titles)

        all_topics = []

        # Fetch from all RSS feeds in parallel
        tasks = [
            self._fetch_rss_feed(feed)
            for feed in POLISH_LEGAL_RSS_FEEDS
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error fetching feed: {result}")
                continue
            all_topics.extend(result)

        # Filter by categories if specified
        if categories:
            all_topics = [
                t for t in all_topics
                if self._matches_category(t, categories)
            ]

        # Remove duplicates and already covered
        all_topics = self._deduplicate_topics(all_topics)

        # Calculate scores
        for topic in all_topics:
            topic.relevance_score = self._calculate_relevance(topic)
            topic.freshness_score = self._calculate_freshness(topic)
            topic.seo_potential = self._calculate_seo_potential(topic)

        # Sort by combined score
        all_topics.sort(
            key=lambda t: (t.relevance_score + t.freshness_score + t.seo_potential) / 3,
            reverse=True
        )

        return all_topics[:max_topics]

    async def _fetch_rss_feed(self, feed_config: Dict[str, str]) -> List[DiscoveredTopic]:
        """Fetch and parse RSS feed."""
        topics = []

        try:
            session = await self._get_session()

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; LegitioBot/1.0)"
            }

            async with session.get(feed_config["url"], headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {feed_config['name']}: {response.status}")
                    return []

                content = await response.text()

            # Parse RSS
            feed = feedparser.parse(content)

            for entry in feed.entries[:20]:  # Limit to 20 per feed
                # Extract published date
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6])

                # Skip old entries (older than 30 days)
                if published_at and (datetime.utcnow() - published_at).days > 30:
                    continue

                # Extract description
                description = ""
                if hasattr(entry, 'summary'):
                    description = self._clean_html(entry.summary)[:500]
                elif hasattr(entry, 'description'):
                    description = self._clean_html(entry.description)[:500]

                topic = DiscoveredTopic(
                    title=entry.title,
                    description=description,
                    source=feed_config["name"],
                    source_url=entry.link if hasattr(entry, 'link') else "",
                    category=self._detect_category(entry.title + " " + description),
                    published_at=published_at,
                )

                topics.append(topic)

            logger.info(f"Fetched {len(topics)} topics from {feed_config['name']}")

        except Exception as e:
            logger.error(f"Error fetching {feed_config['name']}: {e}")

        return topics

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from string."""
        if not html:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    def _detect_category(self, text: str) -> str:
        """Detect legal category from text."""
        text_lower = text.lower()

        scores = {}
        for category, keywords in LEGAL_CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=scores.get)
        return "prawo ogólne"

    def _matches_category(self, topic: DiscoveredTopic, categories: List[str]) -> bool:
        """Check if topic matches any of the specified categories."""
        if not categories:
            return True
        return topic.category in categories

    def _deduplicate_topics(self, topics: List[DiscoveredTopic]) -> List[DiscoveredTopic]:
        """Remove duplicate and already covered topics."""
        seen = set()
        unique = []

        for topic in topics:
            # Normalize title for comparison
            normalized = re.sub(r'\W+', ' ', topic.title.lower()).strip()

            # Skip if already seen or covered
            if normalized in seen:
                continue

            # Check against already covered titles
            is_covered = False
            for covered in self._already_covered_titles:
                covered_norm = re.sub(r'\W+', ' ', covered.lower()).strip()
                # Check for significant overlap
                if self._titles_similar(normalized, covered_norm):
                    is_covered = True
                    break

            if is_covered:
                continue

            seen.add(normalized)
            unique.append(topic)

        return unique

    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar."""
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            return False

        intersection = words1 & words2
        union = words1 | words2

        # Jaccard similarity > 0.5 means similar
        return len(intersection) / len(union) > 0.5

    def _calculate_relevance(self, topic: DiscoveredTopic) -> float:
        """Calculate relevance score (0-1)."""
        score = 0.5  # Base score

        # Boost for specific legal keywords
        legal_keywords = [
            "prawo", "ustawa", "przepisy", "sąd", "wyrok",
            "kodeks", "nowelizacja", "zmiana", "obowiązuje",
            "konsument", "pracownik", "najemca", "spadek"
        ]

        text = (topic.title + " " + topic.description).lower()

        for keyword in legal_keywords:
            if keyword in text:
                score += 0.05

        return min(score, 1.0)

    def _calculate_freshness(self, topic: DiscoveredTopic) -> float:
        """Calculate freshness score (0-1)."""
        if not topic.published_at:
            return 0.5

        age_days = (datetime.utcnow() - topic.published_at).days

        if age_days <= 1:
            return 1.0
        elif age_days <= 3:
            return 0.9
        elif age_days <= 7:
            return 0.7
        elif age_days <= 14:
            return 0.5
        elif age_days <= 30:
            return 0.3
        else:
            return 0.1

    def _calculate_seo_potential(self, topic: DiscoveredTopic) -> float:
        """Calculate SEO potential score (0-1)."""
        score = 0.5

        # Good title length (40-70 chars)
        title_len = len(topic.title)
        if 40 <= title_len <= 70:
            score += 0.2
        elif 30 <= title_len <= 80:
            score += 0.1

        # Has numbers (often indicates specific info)
        if re.search(r'\d+', topic.title):
            score += 0.1

        # Has year reference (timely content)
        if "2025" in topic.title or "2024" in topic.title:
            score += 0.15

        # Action words
        action_words = ["jak", "co", "kiedy", "dlaczego", "ile", "gdzie"]
        if any(word in topic.title.lower() for word in action_words):
            score += 0.1

        return min(score, 1.0)

    async def get_topic_with_ai_suggestions(
        self,
        topic: DiscoveredTopic,
        claude_client,
    ) -> DiscoveredTopic:
        """
        Enhance topic with AI-generated suggestions.

        Args:
            topic: The discovered topic
            claude_client: Claude API client

        Returns:
            Enhanced topic with AI suggestions
        """
        prompt = f"""Przeanalizuj poniższy temat prawny i zaproponuj:

TEMAT: {topic.title}
OPIS: {topic.description}
ŹRÓDŁO: {topic.source}
KATEGORIA: {topic.category}

Odpowiedz w formacie JSON:
{{
    "suggested_title": "Tytuł artykułu SEO (50-60 znaków, zawiera główne keyword)",
    "suggested_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "suggested_angle": "Unikalne podejście do tematu - co wyróżni nasz artykuł (1-2 zdania)"
}}

TYLKO JSON, bez dodatkowego tekstu."""

        try:
            response, _ = await claude_client.generate_text(
                prompt=prompt,
                max_tokens=500,
            )

            # Parse JSON response
            import json
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                topic.suggested_title = data.get("suggested_title", topic.title)
                topic.suggested_keywords = data.get("suggested_keywords", [])
                topic.suggested_angle = data.get("suggested_angle", "")

        except Exception as e:
            logger.error(f"Error getting AI suggestions: {e}")
            topic.suggested_title = topic.title
            topic.suggested_keywords = self._extract_basic_keywords(topic.title)

        return topic

    def _extract_basic_keywords(self, title: str) -> List[str]:
        """Extract basic keywords from title."""
        # Remove common words
        stop_words = {
            "w", "na", "z", "do", "od", "i", "a", "o", "dla", "po",
            "to", "co", "jak", "czy", "lub", "oraz", "przez", "ze"
        }

        words = re.findall(r'\w+', title.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 3]

        return keywords[:5]


# Global instance
_topic_discovery_service: Optional[TopicDiscoveryService] = None


def get_topic_discovery_service() -> TopicDiscoveryService:
    """Get global topic discovery service instance."""
    global _topic_discovery_service
    if _topic_discovery_service is None:
        _topic_discovery_service = TopicDiscoveryService()
    return _topic_discovery_service
