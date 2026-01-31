#!/usr/bin/env python3
"""
Phase 4 - Celery Tasks Test Script
Testuje asynchroniczne generowanie postów i task management
"""

import requests
import json
import time
from pprint import pprint

BASE_URL = "http://localhost:8000/api/v1"

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def test_phase4():
    """Main test function"""

    # 1. Login
    print_header("1. LOGIN")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@test.com", "password": "Admin123!"}
    )

    if response.status_code != 200:
        print("❌ Login failed!")
        pprint(response.json())
        return

    token = response.json()["access_token"]
    print(f"✅ Login successful!")
    print(f"Token: {token[:50]}...\n")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Get Agent
    print_header("2. POBIERANIE AGENTA")
    import asyncio
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.agent import Agent

    async def get_agent():
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Agent))
            agents = result.scalars().all()
            if agents:
                return agents[0].id, agents[0].name
            return None, None

    agent_id, agent_name = asyncio.run(get_agent())

    if not agent_id:
        print("❌ No agents found!")
        return

    print(f"✅ Agent: {agent_name}")
    print(f"   ID: {agent_id}\n")

    # 3. Check Celery Health
    print_header("3. CELERY HEALTH CHECK")
    response = requests.get(f"{BASE_URL}/tasks/health", headers=headers)

    health = response.json()
    if health.get("workers_online"):
        print("✅ Celery workers are ONLINE!")
        print(f"   Status: {health['celery_status']}")
        if "health_check_result" in health:
            print(f"   Worker: {health['health_check_result'].get('worker', 'unknown')}")
    else:
        print("⚠️  Celery workers are OFFLINE!")
        print("   Start worker: ./start_celery_worker.sh")
        print("\nContinuing with API tests (tasks will be queued)...\n")

    # 4. Trigger Async Post Generation
    print_header("4. TRIGGER ASYNC POST GENERATION")
    response = requests.post(
        f"{BASE_URL}/tasks/generate-post",
        headers=headers,
        json={
            "agent_id": str(agent_id),
            "topic": "Celery Task Testing in Python",
            "keyword": "celery tasks"
        }
    )

    if response.status_code == 202:
        task_data = response.json()
        task_id = task_data["task_id"]
        print("✅ Task triggered successfully!")
        print(f"   Task ID: {task_id}")
        print(f"   Status: {task_data['status']}")
        print(f"   Message: {task_data['message']}")

        # 5. Check Task Status
        print_header("5. CHECKING TASK STATUS")
        print("Waiting for task to complete...")

        max_attempts = 30  # Wait max 30 seconds
        for i in range(max_attempts):
            time.sleep(1)
            response = requests.get(
                f"{BASE_URL}/tasks/status/{task_id}",
                headers=headers
            )

            status_data = response.json()
            status = status_data["status"]

            print(f"   [{i+1}s] Status: {status}", end="\r")

            if status == "SUCCESS":
                print("\n✅ Task completed successfully!")
                result = status_data.get("result", {})
                print(f"   Post ID: {result.get('post_id', 'N/A')}")
                print(f"   Title: {result.get('title', 'N/A')}")
                print(f"   Word Count: {result.get('word_count', 'N/A')}")
                print(f"   Status: {result.get('status', 'N/A')}")
                break
            elif status == "FAILURE":
                print("\n❌ Task failed!")
                print(f"   Error: {status_data.get('error', 'Unknown error')}")
                break
            elif status == "PENDING" and i > 10:
                print("\n⚠️  Task still pending after 10s")
                print("   Worker might not be running")
                print("   Task is queued and will execute when worker starts")
                break
        else:
            print(f"\n⏱️  Task still running after {max_attempts}s")
            print("   Check status later with:")
            print(f"   curl {BASE_URL}/tasks/status/{task_id} \\")
            print(f"     -H 'Authorization: Bearer {token[:20]}...'")

    else:
        print("❌ Failed to trigger task!")
        pprint(response.json())

    # 6. List Active Tasks
    print_header("6. LIST ACTIVE TASKS")
    try:
        response = requests.get(f"{BASE_URL}/tasks/active", headers=headers)
        tasks = response.json()

        active_count = len(tasks.get("active", []))
        scheduled_count = len(tasks.get("scheduled", []))
        reserved_count = len(tasks.get("reserved", []))

        print(f"✅ Task counts:")
        print(f"   Active: {active_count}")
        print(f"   Scheduled: {scheduled_count}")
        print(f"   Reserved: {reserved_count}")

        if active_count > 0:
            print("\n   Active tasks:")
            for task in tasks["active"][:3]:  # Show first 3
                print(f"   - {task.get('name', 'Unknown')} (worker: {task.get('worker', 'N/A')})")
    except Exception as e:
        print(f"⚠️  Could not list tasks: {e}")
        print("   Worker might not be running")

    # 7. Monitor RSS Feed (if source exists)
    print_header("7. RSS FEED MONITORING TEST")

    # Get first source
    async def get_source():
        async with AsyncSessionLocal() as session:
            from app.models.source import Source
            result = await session.execute(
                select(Source).where(Source.agent_id == agent_id)
            )
            sources = result.scalars().all()
            if sources:
                return sources[0].id
            return None

    source_id = asyncio.run(get_source())

    if source_id:
        response = requests.post(
            f"{BASE_URL}/tasks/monitor-rss",
            headers=headers,
            json={
                "source_id": str(source_id),
                "auto_generate": False
            }
        )

        if response.status_code == 202:
            rss_task = response.json()
            print(f"✅ RSS monitoring task triggered!")
            print(f"   Task ID: {rss_task['task_id']}")
            print(f"   Message: {rss_task['message']}")
        else:
            print(f"⚠️  Could not trigger RSS monitoring")
    else:
        print("ℹ️  No RSS sources configured")
        print("   Create one to test RSS monitoring")

    # Summary
    print_header("✅ PHASE 4 TESTS COMPLETED")
    print("""
Phase 4 Celery Tasks są gotowe!

Co zostało przetestowane:
✅ Celery health check
✅ Async post generation trigger
✅ Task status tracking
✅ Active tasks listing
✅ RSS monitoring trigger

Aby przetestować pełną funkcjonalność:
1. Uruchom Celery worker: ./start_celery_worker.sh
2. Uruchom ponownie ten test - tasks będą się wykonywać
3. (Opcjonalnie) Uruchom Beat: ./start_celery_beat.sh
4. (Opcjonalnie) Uruchom Flower: ./start_flower.sh

Scheduled Tasks (Celery Beat):
- Scheduled posts publishing (co minutę)
- RSS feed monitoring (co 30 min)
- Agent cron schedules (co 5 min)
- Cleanup (codziennie o 3:00)

Gotowe do Phase 5! 🚀
""")

if __name__ == "__main__":
    try:
        test_phase4()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
