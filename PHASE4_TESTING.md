# Phase 4 - Instrukcja Testowania

## Quick Start - Najprostszy Test ⭐

### Opcja 1: Automatyczny Test (REKOMENDOWANE)

```bash
cd backend
source venv/bin/activate
python3 test_phase4.py
```

**Ten skrypt automatycznie:**
- ✅ Loguje się
- ✅ Sprawdza Celery health
- ✅ Triggeruje async post generation
- ✅ Monitoruje status taska
- ✅ Listuje active tasks
- ✅ Testuje RSS monitoring

---

## Pełny Test z Celery Worker

### Krok 1: Uruchom Celery Worker (nowy terminal)

```bash
cd backend
./start_celery_worker.sh
```

**Oczekiwany output:**
```
Starting Celery Worker...
Queues: generation, publishing, sources, maintenance

 -------------- celery@hostname v5.3.6
--- ***** -----
-- ******* ---- Darwin-24.6.0
- *** --- * ---
- ** ---------- [config]
- ** ---------- .> app:         auto_blog:0x...
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/0
- *** --- * --- .> concurrency: 4
-- ******* ---- .> task events: OFF
--- ***** -----
 -------------- [queues]
                .> generation
                .> publishing
                .> sources
                .> maintenance

[tasks]
  . app.tasks.post_tasks.generate_post_for_agent
  . app.tasks.publishing_tasks.publish_post
  . app.tasks.source_tasks.monitor_rss_feed
  ...

[2025-12-02 19:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-12-02 19:00:00,000: INFO/MainProcess] celery@hostname ready.
```

✅ Worker jest gotowy gdy widzisz: `celery@hostname ready.`

### Krok 2: Uruchom Test (nowy terminal)

```bash
cd backend
source venv/bin/activate
python3 test_phase4.py
```

**Co się stanie:**
1. Zaloguje się jako admin
2. Sprawdzi czy worker działa (powinno być ✅ ONLINE)
3. Wyśle task do wygenerowania posta
4. Będzie sprawdzać status co sekundę
5. Po 10-60s zobaczysz wynik generowania!

---

## Test Manual (bez skryptu)

### 1. Login i Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Admin123!"}' \
  > /tmp/login.json

TOKEN=$(cat /tmp/login.json | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
echo "Token: $TOKEN"
```

### 2. Health Check

```bash
curl http://localhost:8000/api/v1/tasks/health \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Oczekiwany output (worker ONLINE):**
```json
{
  "celery_status": "healthy",
  "workers_online": true,
  "health_check_result": {
    "success": true,
    "timestamp": "2025-12-02T19:00:00",
    "worker": "celery@hostname",
    "database": "connected"
  }
}
```

**Output gdy worker OFFLINE:**
```json
{
  "celery_status": "unhealthy",
  "workers_online": false,
  "error": "..."
}
```

### 3. Trigger Async Post Generation

```bash
# Get agent ID first
AGENT_ID="d880e6d6-0aab-4465-baed-dc116eebd87e"

# Trigger task
curl -X POST http://localhost:8000/api/v1/tasks/generate-post \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "'$AGENT_ID'",
    "topic": "Testing Celery Background Tasks",
    "keyword": "celery python"
  }' | python3 -m json.tool
```

**Response:**
```json
{
  "task_id": "abc-123-def-456-789",
  "status": "pending",
  "message": "Post generation started"
}
```

**Zapisz task_id!**

### 4. Sprawdź Status Taska

```bash
TASK_ID="abc-123-def-456-789"

# Sprawdź status
curl http://localhost:8000/api/v1/tasks/status/$TASK_ID \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Status: PENDING** (czeka na wykonanie)
```json
{
  "task_id": "abc-123-def-456-789",
  "status": "PENDING"
}
```

**Status: STARTED** (wykonuje się)
```json
{
  "task_id": "abc-123-def-456-789",
  "status": "STARTED"
}
```

**Status: SUCCESS** (zakończony)
```json
{
  "task_id": "abc-123-def-456-789",
  "status": "SUCCESS",
  "result": {
    "success": true,
    "post_id": "generated-post-uuid",
    "title": "Testing Celery Background Tasks: Complete Guide",
    "word_count": 1500,
    "status": "draft"
  }
}
```

**Status: FAILURE** (błąd)
```json
{
  "task_id": "abc-123-def-456-789",
  "status": "FAILURE",
  "error": "Error message here"
}
```

### 5. Lista Active Tasks

```bash
curl http://localhost:8000/api/v1/tasks/active \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Response:**
```json
{
  "active": [
    {
      "id": "task-id-1",
      "name": "app.tasks.post_tasks.generate_post_for_agent",
      "worker": "celery@hostname"
    }
  ],
  "scheduled": [],
  "reserved": []
}
```

---

## Test Celery Beat (Scheduled Tasks)

### Krok 1: Uruchom Beat (nowy terminal)

```bash
cd backend
./start_celery_beat.sh
```

**Oczekiwany output:**
```
Starting Celery Beat Scheduler...
Scheduled tasks:
  - Check scheduled posts (every minute)
  - Monitor RSS feeds (every 30 minutes)
  - Process agent schedules (every 5 minutes)
  - Cleanup old results (daily at 3 AM)

celery beat v5.3.6 is starting.
LocalTime -> 2025-12-02 19:00:00
Configuration ->
    . broker -> redis://localhost:6379/0
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> celery.beat.PersistentScheduler

[2025-12-02 19:00:00,000: INFO/MainProcess] beat: Starting...
```

### Krok 2: Zaplanuj Post

```bash
# Najpierw wygeneruj post (jak w kroku 3 powyżej)
# Potem zaplanuj go:

POST_ID="generated-post-uuid"
PUBLISHER_ID="publisher-uuid-or-null"

curl -X POST http://localhost:8000/api/v1/posts/$POST_ID/schedule \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_at": "2025-12-02T19:05:00Z",
    "publisher_id": null
  }' | python3 -m json.tool
```

**Co się stanie:**
1. Post status → `"scheduled"`
2. Celery Beat sprawdza co minutę
3. O 19:05 Beat wykryje post
4. Wyśle task `publish_post` do workera
5. Post się opublikuje
6. Status → `"published"`

### Krok 3: Monitoruj Logi

W terminalu z Beat zobaczysz:
```
[2025-12-02 19:00:00,000: INFO/MainProcess] Scheduler: Sending due task check-scheduled-posts
[2025-12-02 19:05:00,000: INFO/MainProcess] Scheduler: Sending due task check-scheduled-posts
```

W terminalu z Worker zobaczysz:
```
[2025-12-02 19:05:00,123: INFO/MainProcess] Task app.tasks.publishing_tasks.publish_scheduled_posts received
[2025-12-02 19:05:00,456: INFO/ForkPoolWorker-1] Triggered publication for scheduled post abc-123
[2025-12-02 19:05:00,789: INFO/MainProcess] Task app.tasks.publishing_tasks.publish_scheduled_posts succeeded
```

---

## Test RSS Monitoring z Auto-Generation

```bash
# Trigger RSS monitoring z auto-generacją
SOURCE_ID="source-uuid-from-phase3"

curl -X POST http://localhost:8000/api/v1/tasks/monitor-rss \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "'$SOURCE_ID'",
    "auto_generate": true
  }' | python3 -m json.tool
```

**Co się stanie:**
1. Worker pobierze RSS feed
2. Znajdzie najnowsze artykuły (max 3)
3. Dla każdego artykułu wyśle task `generate_post_for_agent`
4. Posty wygenerują się automatycznie!
5. Możesz sprawdzić w `/api/v1/posts`

---

## Test z Flower (Web UI)

### Uruchom Flower (nowy terminal)

```bash
cd backend
./start_flower.sh
```

**Otwórz w przeglądarce:**
```
http://localhost:5555
```

**Co zobaczysz:**
- 📊 Dashboard z statystykami
- 👷 Lista workerów (celery@hostname)
- 📋 Lista tasków (active, completed, failed)
- 🔍 Szczegóły każdego taska
- ⚡ Real-time monitoring

**Możesz:**
- Kliknąć na task → zobaczyć szczegóły, args, result
- Revoke task (anulować)
- Zobacz logs
- Zobacz statistics

---

## Troubleshooting

### ❌ "workers_online": false

**Przyczyna**: Worker nie działa

**Rozwiązanie**:
```bash
# Terminal 1 - uruchom worker
cd backend
./start_celery_worker.sh
```

### ❌ Task stuck na "PENDING"

**Przyczyna**: Worker nie odbiera tasków

**Rozwiązanie**:
1. Sprawdź czy worker działa: `ps aux | grep celery`
2. Sprawdź Redis: `redis-cli ping` → `PONG`
3. Restart worker

### ❌ Import errors w worker

**Przyczyna**: Worker nie może zaimportować modules

**Rozwiązanie**:
```bash
# Upewnij się że venv jest aktywny w terminalu worker
source venv/bin/activate
./start_celery_worker.sh
```

### ⚠️ Task fails with quota error

**To jest OK!** - quota checking działa

**Rozwiązanie**: Zwiększ limity w tenants:
```bash
curl -X PUT http://localhost:8000/api/v1/tenants/{tenant_id} \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"tokens_limit": 1000000}'
```

---

## Quick Commands Reference

```bash
# Check Redis
redis-cli ping

# Check worker processes
ps aux | grep celery

# Kill all Celery processes
pkill -f celery

# View Redis queue length
redis-cli llen celery

# View task keys in Redis
redis-cli keys "celery-task-meta-*"

# Clear all Celery tasks from Redis (CAUTION!)
redis-cli flushdb
```

---

## Summary Checklist

### Minimalne testy (bez workera):
- ✅ Health check (pokaże offline ale API działa)
- ✅ Trigger tasks (będą kolejkowane)
- ✅ Check status (będą pending)

### Pełne testy (z workerem):
- ✅ Health check → workers online
- ✅ Generate post → SUCCESS
- ✅ Monitor RSS → SUCCESS
- ✅ List active tasks → wyświetla running tasks

### Advanced testy (z Beat):
- ✅ Schedule post → auto-publishes at time
- ✅ Agent cron → auto-generates on schedule
- ✅ RSS auto-generation → periodic monitoring

### Web UI test (z Flower):
- ✅ Dashboard widoczny
- ✅ Workers listed
- ✅ Tasks trackable

---

**Dokumentacja**: PHASE4_COMPLETE.md
**Server**: http://localhost:8000
**Flower**: http://localhost:5555
