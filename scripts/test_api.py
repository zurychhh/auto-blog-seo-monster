#!/usr/bin/env python3
"""
Test API for admin@test.com user.
"""
import requests
import json

API_BASE = "http://127.0.0.1:8001/api/v1"

# 1. Login
print("=" * 80)
print("TESTING API FOR admin@test.com")
print("=" * 80)

login_response = requests.post(
    f"{API_BASE}/auth/login",
    json={"email": "admin@legitio.pl", "password": "Admin123!"}
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"\n✅ Login successful!")
    print(f"Token: {token[:50]}...")

    # 2. Get agents
    print("\n" + "-" * 80)
    print("FETCHING AGENTS")
    print("-" * 80)

    agents_response = requests.get(
        f"{API_BASE}/agents",
        headers={"Authorization": f"Bearer {token}"}
    )

    if agents_response.status_code == 200:
        agents = agents_response.json()
        print(f"\n✅ Found {len(agents)} agent(s):")
        for agent in agents:
            print(f"\n   Name: {agent['name']}")
            print(f"   ID: {agent['id']}")
            print(f"   Tone: {agent['tone_style']}")
            print(f"   Language: {agent.get('settings', {}).get('language', 'N/A')}")
    else:
        print(f"\n❌ Error fetching agents: {agents_response.status_code}")
        print(agents_response.text)

    # 3. Get posts
    print("\n" + "-" * 80)
    print("FETCHING POSTS")
    print("-" * 80)

    posts_response = requests.get(
        f"{API_BASE}/posts",
        headers={"Authorization": f"Bearer {token}"}
    )

    if posts_response.status_code == 200:
        posts = posts_response.json()
        print(f"\n✅ Found {len(posts)} post(s):")
        for post in posts:
            print(f"\n   Title: {post['title']}")
            print(f"   ID: {post['id']}")
            print(f"   Status: {post['status']}")
            print(f"   Word count: {post['word_count']}")
    else:
        print(f"\n❌ Error fetching posts: {posts_response.status_code}")
        print(posts_response.text)

else:
    print(f"\n❌ Login failed: {login_response.status_code}")
    print(login_response.text)

print("\n" + "=" * 80)
