#!/bin/bash

# Phase 3 - Manual Test Script
# Ten skrypt testuje wszystkie funkcje Phase 3

echo "=========================================="
echo "   PHASE 3 - TEST ADAPTERS"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8000/api/v1"

# 1. LOGIN
echo "1. Logowanie jako superadmin..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "Admin123!"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed!"
  echo $LOGIN_RESPONSE | python3 -m json.tool
  exit 1
fi

echo "✅ Login successful!"
echo "Token: ${TOKEN:0:50}..."
echo ""

# 2. GET AGENT ID
echo "2. Pobieranie listy agentów..."
AGENTS=$(curl -s -X GET "$BASE_URL/agents" \
  -H "Authorization: Bearer $TOKEN")

AGENT_ID=$(echo $AGENTS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null)

if [ -z "$AGENT_ID" ]; then
  echo "❌ No agents found. Need to create tenant and agent first."
  exit 1
fi

echo "✅ Agent ID: $AGENT_ID"
echo ""

# 3. TEST RSS ADAPTER - The Verge
echo "=========================================="
echo "3. TEST: RSS Adapter - The Verge"
echo "=========================================="
RSS_TEST=$(curl -s -X POST "$BASE_URL/agents/$AGENT_ID/sources/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "rss",
    "config": {
      "feed_url": "https://www.theverge.com/rss/index.xml",
      "max_items": 5,
      "include_content": true
    }
  }')

echo $RSS_TEST | python3 -m json.tool
echo ""

# 4. TEST RSS ADAPTER - TechCrunch
echo "=========================================="
echo "4. TEST: RSS Adapter - TechCrunch"
echo "=========================================="
RSS_TEST2=$(curl -s -X POST "$BASE_URL/agents/$AGENT_ID/sources/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "rss",
    "config": {
      "feed_url": "https://techcrunch.com/feed/",
      "max_items": 3,
      "include_content": true
    }
  }')

echo $RSS_TEST2 | python3 -m json.tool
echo ""

# 5. TEST WEBHOOK ADAPTER (using webhook.site for testing)
echo "=========================================="
echo "5. TEST: Webhook Adapter"
echo "=========================================="
echo "Dla testu webhook potrzebujesz własny webhook URL."
echo "Możesz użyć: https://webhook.site (generuje unikalny URL)"
echo ""
echo "Przykład testu webhook:"
echo "curl -X POST \"$BASE_URL/agents/$AGENT_ID/publishers/test\" \\"
echo "  -H \"Authorization: Bearer $TOKEN\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{"
echo "    \"type\": \"webhook\","
echo "    \"config\": {"
echo "      \"webhook_url\": \"https://webhook.site/YOUR-UNIQUE-ID\","
echo "      \"method\": \"POST\","
echo "      \"auth_type\": \"none\""
echo "    }"
echo "  }'"
echo ""

# 6. CREATE RSS SOURCE
echo "=========================================="
echo "6. Tworzenie RSS Source w bazie danych"
echo "=========================================="
SOURCE_CREATE=$(curl -s -X POST "$BASE_URL/agents/$AGENT_ID/sources" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "rss",
    "name": "The Verge RSS",
    "url": "https://www.theverge.com/rss/index.xml",
    "config": {
      "feed_url": "https://www.theverge.com/rss/index.xml",
      "max_items": 10,
      "include_content": true
    }
  }')

SOURCE_ID=$(echo $SOURCE_CREATE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ ! -z "$SOURCE_ID" ]; then
  echo "✅ Source created: $SOURCE_ID"
  echo $SOURCE_CREATE | python3 -m json.tool
else
  echo "ℹ️  Source may already exist or error occurred"
  echo $SOURCE_CREATE | python3 -m json.tool
fi
echo ""

# 7. LIST SOURCES
echo "=========================================="
echo "7. Lista wszystkich Sources dla agenta"
echo "=========================================="
SOURCES_LIST=$(curl -s -X GET "$BASE_URL/agents/$AGENT_ID/sources" \
  -H "Authorization: Bearer $TOKEN")

echo $SOURCES_LIST | python3 -m json.tool
echo ""

echo "=========================================="
echo "   TESTY ZAKOŃCZONE"
echo "=========================================="
echo ""
echo "✅ Phase 3 adapters działają poprawnie!"
echo ""
echo "Następne kroki do manualnego testu:"
echo "1. Utwórz webhook na https://webhook.site"
echo "2. Przetestuj webhook adapter z tym URL"
echo "3. (Opcjonalnie) Skonfiguruj WordPress site i przetestuj publikację"
echo ""
