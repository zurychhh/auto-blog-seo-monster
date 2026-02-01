"""
Topic suggestions API endpoint.
Uses Claude AI to generate content topic suggestions based on agent expertise.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.post import Post
from app.api.deps import get_current_user
from app.ai.claude_client import get_claude_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topics", tags=["Topics"])


class TopicSuggestRequest(BaseModel):
    agent_id: UUID
    count: int = Field(default=5, ge=1, le=10)


class TopicSuggestion(BaseModel):
    topic: str
    target_keyword: str
    reasoning: str


class TopicSuggestResponse(BaseModel):
    suggestions: List[TopicSuggestion]
    agent_id: str


@router.post("/suggest", response_model=TopicSuggestResponse)
async def suggest_topics(
    request: TopicSuggestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate AI-powered topic suggestions based on agent expertise."""

    # Get agent and verify access
    result = await db.execute(
        select(Agent).where(Agent.id == request.agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if not current_user.is_superadmin() and agent.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get recent post titles to avoid duplicates
    posts_result = await db.execute(
        select(Post.title)
        .where(Post.agent_id == request.agent_id)
        .order_by(Post.created_at.desc())
        .limit(20)
    )
    existing_titles = [row[0] for row in posts_result.fetchall()]

    # Build prompt
    existing_list = "\n".join(f"- {t}" for t in existing_titles) if existing_titles else "No posts yet."

    prompt = f"""You are a content strategist for an ecommerce/business blog.

Agent expertise: {agent.expertise}
Agent tone: {agent.tone}
{f'Agent persona: {agent.persona}' if agent.persona else ''}

Already published posts (avoid similar topics):
{existing_list}

Generate exactly {request.count} unique, high-value blog topic suggestions that:
1. Target specific long-tail SEO keywords
2. Are relevant to the agent's expertise
3. Would attract organic search traffic
4. Are different from already published posts
5. Are actionable and specific (not generic)

Return ONLY a valid JSON array with exactly {request.count} objects, each having:
- "topic": the article title (50-80 chars)
- "target_keyword": the primary SEO keyword to target (2-4 words)
- "reasoning": brief explanation of why this topic is valuable (1 sentence)

Example format:
[
  {{"topic": "How Customer Retention Drives 5x More Revenue Than Acquisition", "target_keyword": "customer retention revenue", "reasoning": "High search volume keyword with strong commercial intent for ecommerce brands."}}
]

Return ONLY the JSON array, no other text."""

    # Call Claude
    claude = get_claude_client()
    try:
        text, _tokens = await claude.generate_text(
            prompt=prompt,
            system_prompt="You are a content strategist. Return only valid JSON.",
            max_tokens=1500,
            temperature=0.8,
        )

        # Parse JSON from response
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        suggestions_raw = json.loads(text)

        suggestions = [
            TopicSuggestion(
                topic=s.get("topic", ""),
                target_keyword=s.get("target_keyword", ""),
                reasoning=s.get("reasoning", ""),
            )
            for s in suggestions_raw
            if s.get("topic")
        ]

        return TopicSuggestResponse(
            suggestions=suggestions[:request.count],
            agent_id=str(request.agent_id),
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse topic suggestions",
        )
    except Exception as e:
        logger.error(f"Topic suggestion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate topic suggestions",
        )
