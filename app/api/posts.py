"""
Posts API endpoints - manage blog posts with SEO metadata.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.post import Post
from app.models.user import User
from app.models.agent import Agent
from app.models.publisher import Publisher
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    PostGenerateRequest,
    PostPublishRequest,
    PostScheduleRequest,
    SEOPreviewResponse
)
from app.api.deps import get_current_user
from app.ai.post_generator import get_post_generator
from app.services.seo_service import get_seo_service
from app.services.usage_service import get_usage_service
from app.ai.token_counter import get_token_counter
from app.adapters import create_publisher_adapter
from datetime import datetime

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new post manually (without AI generation).
    Use this for manually written content.
    """
    # Check agent exists and user has access
    result = await db.execute(
        select(Agent).where(Agent.id == post_data.agent_id)
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

    # Generate slug if not provided
    seo_service = get_seo_service()
    slug = post_data.slug or seo_service.generate_slug(post_data.title)

    # Check slug uniqueness
    existing = await db.execute(
        select(Post).where(Post.slug == slug)
    )
    if existing.scalar_one_or_none():
        # Add suffix to make unique
        import uuid
        slug = f"{slug}-{str(uuid.uuid4())[:8]}"

    # Create post
    new_post = Post(
        agent_id=post_data.agent_id,
        title=post_data.title,
        slug=slug,
        content=post_data.content,
        excerpt=post_data.excerpt,
        meta_title=post_data.meta_title,
        meta_description=post_data.meta_description,
        keywords=post_data.keywords or [],
        status=post_data.status,
        publisher_id=post_data.publisher_id,
        word_count=len(post_data.content.split()),
        tokens_used=0,  # Manual post - no AI tokens used
    )

    # Set published_at if status is published
    if post_data.status == "published":
        new_post.published_at = datetime.utcnow()

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    return new_post


@router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List posts with pagination."""
    # Build query based on user role
    query = select(Post)

    if not current_user.is_superadmin():
        # Filter by user's tenant through agents
        query = query.join(Agent).where(Agent.tenant_id == current_user.tenant_id)

    # Filter by status if provided
    if status:
        query = query.where(Post.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Post.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    posts = result.scalars().all()

    return PostListResponse(
        items=posts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get post by ID."""
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Check access
    if not current_user.is_superadmin():
        # Get post's agent to check tenant
        agent_result = await db.execute(
            select(Agent).where(Agent.id == post.agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        if not agent or agent.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return post


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    post_data: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update post content and metadata."""
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Check access
    if not current_user.is_superadmin():
        agent_result = await db.execute(
            select(Agent).where(Agent.id == post.agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        if not agent or agent.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    # Update fields
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post)

    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete post."""
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Check access
    if not current_user.is_superadmin():
        agent_result = await db.execute(
            select(Agent).where(Agent.id == post.agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        if not agent or agent.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    await db.delete(post)
    await db.commit()


@router.post("/generate", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def generate_post(
    generate_data: PostGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate blog post using AI.

    This endpoint:
    1. Checks tenant quotas (tokens and posts)
    2. Generates content using Claude API
    3. Calculates SEO metrics (readability, keyword density)
    4. Logs usage and updates tenant counters
    5. Saves post as draft
    """
    # Check agent exists and user has access
    result = await db.execute(
        select(Agent).where(Agent.id == generate_data.agent_id)
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

    # Check tenant quotas
    usage_service = get_usage_service()
    try:
        quota_status = await usage_service.check_tenant_quota(
            db=db,
            tenant_id=agent.tenant_id,
            tokens_needed=3000,  # Approximate tokens needed
            posts_needed=1,
        )

        if not quota_status["tokens_available"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Token limit exceeded. Remaining: {quota_status['tokens_remaining']}",
            )

        if not quota_status["posts_available"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Posts limit exceeded. Remaining: {quota_status['posts_remaining']}",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Generate post using AI
    try:
        post_generator = get_post_generator()
        seo_service = get_seo_service()
        token_counter = get_token_counter()

        # Generate content
        generation_result = await post_generator.generate_post(
            agent=agent,
            topic=generate_data.topic,
            keyword=generate_data.target_keyword,
            sources_content=None,  # Will be added in Phase 3
        )

        # Calculate SEO metrics
        readability_score = seo_service.calculate_readability_score(
            generation_result["content"]
        )

        keyword_density = {}
        if generation_result["keywords"]:
            keyword_density = seo_service.calculate_keyword_density(
                generation_result["content"],
                generation_result["keywords"]
            )

        # Generate schema markup
        schema_markup = seo_service.generate_schema_markup(
            post_title=generation_result["title"],
            post_content=generation_result["content"],
            author_name=agent.name,
        )

        # Generate slug
        slug = seo_service.generate_slug(generation_result["title"])

        # Create post
        new_post = Post(
            agent_id=agent.id,
            title=generation_result["title"],
            content=generation_result["content"],
            meta_title=generation_result["meta_title"],
            meta_description=generation_result["meta_description"],
            keywords=generation_result["keywords"],
            slug=slug,
            status="draft",
            tokens_used=generation_result["tokens_used"],
            word_count=generation_result["word_count"],
            readability_score=readability_score,
            keyword_density=keyword_density,
        )

        db.add(new_post)
        await db.flush()

        # Estimate cost
        cost = token_counter.estimate_cost(
            input_tokens=generation_result["tokens_used"] // 2,  # Rough estimate
            output_tokens=generation_result["tokens_used"] // 2,
        )

        # Log usage
        await usage_service.log_usage(
            db=db,
            tenant_id=agent.tenant_id,
            action_type="post_generation",
            tokens_used=generation_result["tokens_used"],
            cost=cost,
            agent_id=agent.id,
            meta_data={
                "post_id": str(new_post.id),
                "user_id": str(current_user.id),
                "word_count": generation_result["word_count"],
                "readability_score": readability_score,
                "keyword_density": keyword_density,
            },
        )

        # Update tenant counters
        await usage_service.update_tenant_usage(
            db=db,
            tenant_id=agent.tenant_id,
            tokens_delta=generation_result["tokens_used"],
            posts_delta=1,
        )

        await db.commit()
        await db.refresh(new_post)

        return new_post

    except ValueError as e:
        # Quota exceeded during processing
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        )
    except Exception as e:
        # AI generation failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Post generation failed: {str(e)}",
        )


@router.post("/{post_id}/publish", status_code=status.HTTP_200_OK)
async def publish_post(
    post_id: UUID,
    publish_data: PostPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Publish post to configured publisher.

    Uses publisher adapter to send post to target platform (WordPress, webhook, etc.).
    Updates post status and stores published URL.
    """
    # Get post
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Get agent (for access check and publisher_id)
    agent_result = await db.execute(
        select(Agent).where(Agent.id == post.agent_id)
    )
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check access
    if not current_user.is_superadmin() and agent.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Determine publisher to use
    publisher_id = publish_data.publisher_id or agent.publisher_id

    if not publisher_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No publisher specified. Set publisher_id in request or configure default publisher for agent.",
        )

    # Get publisher
    publisher_result = await db.execute(
        select(Publisher).where(Publisher.id == publisher_id)
    )
    publisher = publisher_result.scalar_one_or_none()

    if not publisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    # Verify publisher belongs to same agent
    if publisher.agent_id != agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Publisher does not belong to this agent",
        )

    # Publish using adapter
    try:
        adapter = create_publisher_adapter(publisher.type, publisher.config)

        result = await adapter.publish(
            title=post.title,
            content=post.content,
            excerpt=post.excerpt,
            meta_title=post.meta_title,
            meta_description=post.meta_description,
            keywords=post.keywords,
            featured_image_url=post.og_image_url,
            status="publish",
        )

        if result.success:
            # Update post with publication details
            post.status = "published"
            post.published_url = result.published_url
            post.published_at = datetime.utcnow()
            post.publisher_id = publisher.id

            await db.commit()
            await db.refresh(post)

            return {
                "success": True,
                "message": "Post published successfully",
                "post_id": str(post_id),
                "published_url": result.published_url,
                "platform_post_id": result.published_id,
            }
        else:
            # Publication failed
            post.status = "failed"
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Publication failed: {result.error}",
            )

    except ValueError as e:
        # Unknown adapter type
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Adapter error
        post.status = "failed"
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Publication error: {str(e)}",
        )


@router.post("/{post_id}/schedule")
async def schedule_post(
    post_id: UUID,
    schedule_data: PostScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Schedule post for future publication."""
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Check access
    if not current_user.is_superadmin():
        agent_result = await db.execute(
            select(Agent).where(Agent.id == post.agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        if not agent or agent.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    post.status = "scheduled"
    post.scheduled_at = schedule_data.scheduled_at
    if schedule_data.publisher_id:
        post.publisher_id = schedule_data.publisher_id

    await db.commit()

    return {
        "message": "Post scheduled",
        "post_id": str(post_id),
        "scheduled_at": post.scheduled_at.isoformat()
    }


class FormatRequest(BaseModel):
    """Request to format content."""
    content: str
    title: Optional[str] = None


@router.post("/format")
async def format_content(
    format_data: FormatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Format raw text/markdown into professional HTML with CSS components.
    Converts markdown to styled HTML with info-boxes, cards, etc.
    """
    import re

    content = format_data.content
    title = format_data.title or ""

    # Convert markdown headers to HTML
    content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^# (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)

    # Convert bold text
    content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'__(.+?)__', r'<strong>\1</strong>', content)

    # Convert italic text
    content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
    content = re.sub(r'_(.+?)_', r'<em>\1</em>', content)

    # Convert blockquotes to info-boxes
    def convert_blockquote(match):
        text = match.group(1).strip()
        # Detect type based on keywords
        if any(kw in text.lower() for kw in ['uwaga', 'warning', 'ostrzeżenie']):
            color = 'yellow'
            icon = 'fa-exclamation-triangle'
        elif any(kw in text.lower() for kw in ['ważne', 'important', 'pamiętaj']):
            color = 'orange'
            icon = 'fa-exclamation-circle'
        elif any(kw in text.lower() for kw in ['wskazówka', 'tip', 'porada']):
            color = 'green'
            icon = 'fa-lightbulb'
        else:
            color = 'blue'
            icon = 'fa-info-circle'

        return f'''<div class="info-box {color}">
<div class="info-box-title"><i class="fas {icon}"></i> Informacja</div>
<p>{text}</p>
</div>'''

    content = re.sub(r'^>\s*(.+)$', convert_blockquote, content, flags=re.MULTILINE)

    # Convert bullet lists
    def convert_list(match):
        items = match.group(0)
        list_items = re.findall(r'^[-*]\s*(.+)$', items, re.MULTILINE)
        if list_items:
            items_html = '\n'.join(f'<li>{item}</li>' for item in list_items)
            return f'<ul>\n{items_html}\n</ul>'
        return items

    content = re.sub(r'(^[-*]\s*.+$\n?)+', convert_list, content, flags=re.MULTILINE)

    # Convert numbered lists
    def convert_numbered_list(match):
        items = match.group(0)
        list_items = re.findall(r'^\d+\.\s*(.+)$', items, re.MULTILINE)
        if list_items:
            items_html = '\n'.join(f'<li>{item}</li>' for item in list_items)
            return f'<ol>\n{items_html}\n</ol>'
        return items

    content = re.sub(r'(^\d+\.\s*.+$\n?)+', convert_numbered_list, content, flags=re.MULTILINE)

    # Wrap plain paragraphs in <p> tags
    lines = content.split('\n')
    formatted_lines = []
    in_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted_lines.append('')
            continue

        # Check if line is already HTML
        if stripped.startswith('<') or in_block:
            formatted_lines.append(line)
            if '<div' in stripped:
                in_block = True
            if '</div>' in stripped:
                in_block = False
        else:
            # Wrap in paragraph
            formatted_lines.append(f'<p>{stripped}</p>')

    content = '\n'.join(formatted_lines)

    # Clean up empty paragraphs
    content = re.sub(r'<p>\s*</p>', '', content)

    # Add section dividers between h2 headers (except first one)
    h2_count = 0
    def add_divider(match):
        nonlocal h2_count
        h2_count += 1
        if h2_count > 1:
            return f'<hr class="section-divider" />\n\n{match.group(0)}'
        return match.group(0)

    content = re.sub(r'<h2>.+?</h2>', add_divider, content)

    # Add disclaimer at the end
    content += '''

<div class="disclaimer-box">
<p><strong>Zastrzeżenie:</strong> Niniejszy artykuł ma charakter wyłącznie informacyjny i edukacyjny. Nie stanowi porady prawnej ani nie zastępuje konsultacji z prawnikiem. Legitio.pl nie ponosi odpowiedzialności za decyzje podjęte na podstawie powyższych informacji.</p>
</div>'''

    return {
        "formatted_content": content.strip(),
        "original_length": len(format_data.content),
        "formatted_length": len(content)
    }
