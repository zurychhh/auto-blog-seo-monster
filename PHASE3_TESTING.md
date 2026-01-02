# Phase 3 - Instrukcja Testowania

## Wymagania
- Server musi być uruchomiony: `http://localhost:8000`
- Credentials: `admin@test.com` / `Admin123!`

## Opcja 1: Python Script (Rekomendowane) ⭐

Najprostszy sposób - automatyczny test wszystkiego:

```bash
cd backend
source venv/bin/activate
python3 test_phase3.py
```

**Co testuje:**
- ✅ Login
- ✅ RSS Adapter - The Verge
- ✅ RSS Adapter - TechCrunch
- ✅ RSS Adapter - Hacker News
- ✅ Tworzenie RSS Source w bazie
- ✅ Listowanie Sources

**Oczekiwany output:**
```
============================================================
  1. LOGIN
============================================================
✅ Login successful!
Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

============================================================
  3. TEST RSS ADAPTER - The Verge
============================================================
✅ RSS Test SUCCESSFUL!
   Feed: The Verge
   Items: 10
   Type: atom10

...
```

## Opcja 2: Bash Script

```bash
cd backend
chmod +x test_phase3.sh
./test_phase3.sh
```

## Opcja 3: Manual Testing (krok po kroku)

### 1. Login i pobierz token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Admin123!"}' \
  | python3 -m json.tool
```

Zapisz `access_token` z odpowiedzi.

### 2. Pobierz Agent ID

```bash
TOKEN="twoj-token-tutaj"

curl -X GET http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

Zapisz `id` pierwszego agenta.

### 3. Test RSS Adapter

```bash
TOKEN="twoj-token"
AGENT_ID="agent-id-tutaj"

curl -X POST "http://localhost:8000/api/v1/agents/$AGENT_ID/sources/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "rss",
    "config": {
      "feed_url": "https://www.theverge.com/rss/index.xml",
      "max_items": 5,
      "include_content": true
    }
  }' | python3 -m json.tool
```

**Oczekiwany wynik:**
```json
{
  "success": true,
  "message": "Successfully connected to feed: The Verge",
  "data": {
    "items_found": 10,
    "feed_type": "atom10"
  }
}
```

### 4. Utwórz RSS Source w bazie

```bash
curl -X POST "http://localhost:8000/api/v1/agents/$AGENT_ID/sources" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "rss",
    "name": "My Tech Feed",
    "url": "https://www.theverge.com/rss/index.xml",
    "config": {
      "feed_url": "https://www.theverge.com/rss/index.xml",
      "max_items": 10,
      "include_content": true
    }
  }' | python3 -m json.tool
```

### 5. Lista wszystkich Sources

```bash
curl -X GET "http://localhost:8000/api/v1/agents/$AGENT_ID/sources" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

## Test Webhook Publisher 🔗

### Krok 1: Utwórz test webhook

1. Idź na: https://webhook.site
2. Skopiuj swój unikalny URL (np. `https://webhook.site/abc-123-def`)

### Krok 2: Test connection

```bash
curl -X POST "http://localhost:8000/api/v1/agents/$AGENT_ID/publishers/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "webhook",
    "config": {
      "webhook_url": "https://webhook.site/YOUR-UNIQUE-ID",
      "method": "POST",
      "auth_type": "none"
    }
  }' | python3 -m json.tool
```

### Krok 3: Sprawdź webhook.site

Powinieneś zobaczyć test request z payload:
```json
{
  "action": "test",
  "message": "Connection test from Auto-Blog SEO Monster"
}
```

## Test WordPress Publisher 🔗

**Wymagania:**
- Live WordPress site (5.6+)
- WordPress Application Password

### Krok 1: Utwórz Application Password w WordPress

1. WordPress Admin → Users → Your Profile
2. Scroll do "Application Passwords"
3. Nazwa: "Auto-Blog API"
4. Click "Add New Application Password"
5. Skopiuj wygenerowane hasło (format: `xxxx xxxx xxxx xxxx xxxx xxxx`)

### Krok 2: Test connection

```bash
curl -X POST "http://localhost:8000/api/v1/agents/$AGENT_ID/publishers/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "wordpress",
    "config": {
      "site_url": "https://your-site.com",
      "username": "your-wp-username",
      "password": "xxxx xxxx xxxx xxxx xxxx xxxx",
      "convert_markdown": true
    }
  }' | python3 -m json.tool
```

**Expected success:**
```json
{
  "success": true,
  "message": "Successfully connected to WordPress",
  "platform_info": {
    "name": "Your Site Name",
    "url": "https://your-site.com",
    "version": "6.x.x"
  }
}
```

## Test Publikacji Posta 📝

### 1. Wygeneruj post (z Phase 2)

```bash
curl -X POST http://localhost:8000/api/v1/posts/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "'$AGENT_ID'",
    "topic": "AI and Machine Learning in 2024",
    "target_keyword": "artificial intelligence"
  }' | python3 -m json.tool
```

Zapisz `id` wygenerowanego posta.

### 2. Utwórz Publisher

```bash
# Webhook Publisher
curl -X POST "http://localhost:8000/api/v1/agents/$AGENT_ID/publishers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "webhook",
    "name": "My Webhook",
    "config": {
      "webhook_url": "https://webhook.site/YOUR-ID",
      "method": "POST",
      "auth_type": "none"
    }
  }' | python3 -m json.tool
```

Zapisz `id` publishera.

### 3. Publikuj post

```bash
POST_ID="post-id-tutaj"
PUBLISHER_ID="publisher-id-tutaj"

curl -X POST "http://localhost:8000/api/v1/posts/$POST_ID/publish" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "publisher_id": "'$PUBLISHER_ID'"
  }' | python3 -m json.tool
```

**Expected success:**
```json
{
  "success": true,
  "message": "Post published successfully",
  "published_url": "https://...",
  "platform_post_id": "123"
}
```

### 4. Sprawdź status posta

```bash
curl -X GET "http://localhost:8000/api/v1/posts/$POST_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

Sprawdź:
- `status` = `"published"`
- `published_url` - URL opublikowanego posta
- `published_at` - timestamp publikacji

## Dodatkowe RSS Feeds do testowania

```bash
# TechCrunch
"feed_url": "https://techcrunch.com/feed/"

# Hacker News
"feed_url": "https://news.ycombinator.com/rss"

# BBC Technology
"feed_url": "http://feeds.bbci.co.uk/news/technology/rss.xml"

# Wired
"feed_url": "https://www.wired.com/feed/rss"

# Ars Technica
"feed_url": "http://feeds.arstechnica.com/arstechnica/index"
```

## Troubleshooting

### Problem: 401 Unauthorized
```bash
# Token wygasł lub nieprawidłowy - zaloguj się ponownie
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Admin123!"}'
```

### Problem: 404 Not Found
```bash
# Sprawdź czy server działa
curl http://localhost:8000/docs
```

### Problem: No agents found
```bash
# Lista agentów
curl -X GET http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN"
```

## Quick Test - One Command

Najszybszy test - czy wszystko działa:

```bash
cd backend && source venv/bin/activate && python3 test_phase3.py
```

---

**Status**: ✅ Phase 3 Ready for Testing
**Documentation**: PHASE3_COMPLETE.md
**Server**: http://localhost:8000
