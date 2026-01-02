# Phase 4 - Celery Scheduler & Background Tasks - COMPLETE ✓

## Implementacja

### 1. Celery Configuration

**File**: `app/celery_app.py`

**Features**:
- Redis broker + backend
- 4 task queues: generation, publishing, sources, maintenance
- Retry logic with exponential backoff
- Task time limits (1 hour max, 50 min soft)
- Celery Beat scheduler with cron jobs

**Beat Schedule** (automatic tasks):
```python
{
    "check-scheduled-posts": Every 1 minute,
    "monitor-rss-feeds": Every 30 minutes,
    "process-agent-schedules": Every 5 minutes,
    "cleanup-task-results": Daily at 3 AM UTC,
}
```

### 2. Task Modules

#### **Post Tasks** (`app/tasks/post_tasks.py`)
- `generate_post_for_agent(agent_id, topic, keyword)` - Generate blog post
- `process_agent_schedules()` - Check and trigger agent cron schedules
- Auto-retry: 3 attempts with backoff

**Features**:
- Quota checking before generation
- Source content integration
- SEO metrics calculation
- Usage tracking and cost logging

#### **Publishing Tasks** (`app/tasks/publishing_tasks.py`)
- `publish_post(post_id, publisher_id)` - Publish to platform
- `publish_scheduled_posts()` - Publish posts with scheduled_at <= now
- `retry_failed_publications()` - Retry all failed posts

**Features**:
- Publisher adapter integration
- Status updates (published/failed)
- Automatic scheduled publishing every minute

#### **Source Tasks** (`app/tasks/source_tasks.py`)
- `monitor_rss_feed(source_id, auto_generate)` - Fetch RSS feed
- `monitor_all_rss_feeds()` - Monitor all feeds (every 30 min)
- `test_source_connection(source_id)` - Test source config

**Features**:
- Auto-generate posts from RSS items
- Configurable auto_generate flag
- Multi-source support

#### **Maintenance Tasks** (`app/tasks/maintenance_tasks.py`)
- `cleanup_old_results()` - Remove old task results (daily)
- `health_check()` - Verify Celery + DB connectivity

### 3. API Endpoints

**Base**: `/api/v1/tasks`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate-post` | POST | Trigger async post generation |
| `/publish-post` | POST | Trigger async publishing |
| `/monitor-rss` | POST | Trigger RSS monitoring |
| `/retry-failed` | POST | Retry all failed publications |
| `/status/{task_id}` | GET | Get task status/result |
| `/cancel/{task_id}` | DELETE | Cancel running task |
| `/active` | GET | List active/scheduled tasks |
| `/health` | GET | Check Celery workers health |

**Task Statuses**:
- `PENDING` - Waiting to execute
- `STARTED` - Running
- `SUCCESS` - Completed successfully
- `FAILURE` - Failed
- `RETRY` - Retrying
- `REVOKED` - Cancelled

### 4. Retry Logic

**Built-in for all tasks**:
```python
autoretry_for=(Exception,)
retry_backoff=True
retry_backoff_max=600  # 10 minutes
max_retries=3
```

**Exponential backoff**: 2s, 4s, 8s, 16s, ... up to 10 minutes

### 5. Helper Scripts

```bash
# Start Celery Worker (processes tasks)
./start_celery_worker.sh

# Start Celery Beat (scheduler)
./start_celery_beat.sh

# Start Flower (web UI monitoring)
./start_flower.sh  # http://localhost:5555
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                       │
│                  (http://localhost:8000)                      │
│                                                               │
│  POST /api/v1/tasks/generate-post                            │
│        ↓                                                      │
│  celery_app.send_task()                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      Redis Broker                            │
│                  (redis://localhost:6379/0)                  │
│                                                               │
│  Queues: [generation, publishing, sources, maintenance]      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Celery Worker                              │
│               (./start_celery_worker.sh)                      │
│                                                               │
│  - Picks tasks from queues                                   │
│  - Executes task functions                                   │
│  - Stores results in Redis                                   │
│  - Auto-retries on failure                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Celery Beat                                │
│               (./start_celery_beat.sh)                        │
│                                                               │
│  Every 1 min → publish_scheduled_posts()                     │
│  Every 5 min → process_agent_schedules()                     │
│  Every 30 min → monitor_all_rss_feeds()                      │
│  Daily 3 AM → cleanup_old_results()                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      Flower (Optional)                        │
│                  (http://localhost:5555)                      │
│                                                               │
│  - Monitor tasks in real-time                                │
│  - View worker status                                        │
│  - Inspect task details                                      │
│  - Retry/revoke tasks via UI                                 │
└─────────────────────────────────────────────────────────────┘
```

## Usage Examples

### 1. Trigger Async Post Generation

```bash
curl -X POST http://localhost:8000/api/v1/tasks/generate-post \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "d880e6d6-0aab-4465-baed-dc116eebd87e",
    "topic": "AI in 2025",
    "keyword": "artificial intelligence"
  }'
```

**Response**:
```json
{
  "task_id": "abc-123-def-456",
  "status": "pending",
  "message": "Post generation started"
}
```

### 2. Check Task Status

```bash
curl http://localhost:8000/api/v1/tasks/status/abc-123-def-456 \
  -H "Authorization: Bearer $TOKEN"
```

**Response (running)**:
```json
{
  "task_id": "abc-123-def-456",
  "status": "STARTED"
}
```

**Response (completed)**:
```json
{
  "task_id": "abc-123-def-456",
  "status": "SUCCESS",
  "result": {
    "success": true,
    "post_id": "post-uuid-here",
    "title": "AI in 2025: Comprehensive Guide",
    "word_count": 1500,
    "status": "draft"
  }
}
```

### 3. Schedule Post for Auto-Publishing

```bash
# Create post with scheduled_at
curl -X POST http://localhost:8000/api/v1/posts/{post_id}/schedule \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "scheduled_at": "2025-12-03T10:00:00Z",
    "publisher_id": "publisher-uuid"
  }'
```

**What happens**:
1. Post status → `"scheduled"`
2. Celery Beat runs `publish_scheduled_posts()` every minute
3. At 10:00 AM UTC, task detects post is due
4. Triggers `publish_post.delay()` async task
5. Post publishes to configured platform
6. Status updates to `"published"`

### 4. Configure Agent Cron Schedule

```bash
# Update agent with schedule_cron
curl -X PUT http://localhost:8000/api/v1/agents/{agent_id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "schedule_cron": "0 9 * * MON"
  }'
```

**Schedule format** (standard cron):
- `0 9 * * MON` - Every Monday at 9 AM
- `0 */4 * * *` - Every 4 hours
- `0 0 * * *` - Daily at midnight
- `0 9 * * 1-5` - Weekdays at 9 AM

**What happens**:
1. Celery Beat runs `process_agent_schedules()` every 5 minutes
2. Checks all agents with `schedule_cron`
3. Uses croniter to check if should run now
4. Triggers `generate_post_for_agent.delay()` if due
5. Post generates automatically

### 5. Monitor RSS with Auto-Generation

```bash
curl -X POST http://localhost:8000/api/v1/tasks/monitor-rss \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "source_id": "source-uuid",
    "auto_generate": true
  }'
```

**What happens**:
1. Fetches latest items from RSS feed
2. If `auto_generate=true`, triggers post generation for each item
3. Uses item title as topic, extracts keyword
4. Max 3 posts per monitoring run (to avoid overwhelming)

## Running Phase 4

### Prerequisites
- Redis running: `redis-cli ping` → `PONG`
- FastAPI server running: http://localhost:8000
- Login credentials: `admin@test.com` / `Admin123!`

### Start Celery Services

**Terminal 1** - Celery Worker:
```bash
cd backend
./start_celery_worker.sh
```

**Terminal 2** - Celery Beat (optional, for scheduled tasks):
```bash
cd backend
./start_celery_beat.sh
```

**Terminal 3** - Flower (optional, for monitoring):
```bash
cd backend
./start_flower.sh
# Open: http://localhost:5555
```

### Quick Test

```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Admin123!"}' \
  > /tmp/login.json

# 2. Get token
TOKEN=$(cat /tmp/login.json | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# 3. Check Celery health
curl http://localhost:8000/api/v1/tasks/health \
  -H "Authorization: Bearer $TOKEN"

# 4. Trigger test task
curl -X POST http://localhost:8000/api/v1/tasks/generate-post \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "d880e6d6-0aab-4465-baed-dc116eebd87e",
    "topic": "Testing Celery",
    "keyword": "test"
  }'
```

## Monitoring

### Via Flower (Web UI)
- URL: http://localhost:5555
- Features: Real-time task monitoring, worker stats, task history

### Via API
```bash
# List active tasks
curl http://localhost:8000/api/v1/tasks/active \
  -H "Authorization: Bearer $TOKEN"

# Check specific task
curl http://localhost:8000/api/v1/tasks/status/{task_id} \
  -H "Authorization: Bearer $TOKEN"
```

### Via Redis CLI
```bash
# Check queue lengths
redis-cli llen celery

# View task results (example)
redis-cli keys "celery-task-meta-*"
```

## Troubleshooting

### Worker not picking up tasks
```bash
# Check Redis connection
redis-cli ping

# Check worker is running
ps aux | grep celery

# Restart worker
pkill -f "celery worker"
./start_celery_worker.sh
```

### Beat not triggering scheduled tasks
```bash
# Check Beat is running
ps aux | grep "celery beat"

# Check celerybeat-schedule file
ls -la celerybeat-schedule

# Restart Beat (will recreate schedule)
pkill -f "celery beat"
./start_celery_beat.sh
```

### Task stuck in PENDING
- Worker might not be running
- Task might be in wrong queue
- Check worker logs for errors

## Summary

### ✅ Completed

1. **Celery App** - Full configuration with 4 queues
2. **Post Tasks** - Scheduled generation, agent cron schedules
3. **Publishing Tasks** - Scheduled publishing, retry logic
4. **Source Tasks** - RSS monitoring with auto-generation
5. **Maintenance Tasks** - Cleanup, health checks
6. **API Endpoints** - 8 endpoints for task management
7. **Beat Schedule** - 4 cron jobs configured
8. **Retry Logic** - Exponential backoff, 3 retries
9. **Helper Scripts** - Easy start/stop for services
10. **Documentation** - Complete usage guide

### 🚀 Ready for Production

Phase 4 is complete and tested. The system can now:
- Generate posts asynchronously
- Publish on schedule
- Monitor RSS feeds automatically
- Process agent cron schedules
- Retry failed operations
- Scale horizontally (add more workers)

### Next: Phase 5

**Phase 5: React Frontend**
- Dashboard with analytics
- Agent management UI
- Post editor
- Source/Publisher configuration
- Task monitoring interface

---

**Status**: ✅ PHASE 4 COMPLETE
**Date**: 2025-12-02
**Server**: http://localhost:8000
**Celery**: Redis broker ready
**Flower**: http://localhost:5555
