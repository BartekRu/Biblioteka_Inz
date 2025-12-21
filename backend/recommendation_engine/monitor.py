import requests
import time
import os
import sys

BASE_URL = "http://localhost:8000"

USERNAME = "Tomek"
PASSWORD = "Haslo12!" 
REFRESH_SEC = 5


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def login(username, password):
    resp = requests.post(
        f"{BASE_URL}/v1/auth/token", data={"username": username, "password": password}
    )
    if resp.status_code != 200:
        print("❌ Login failed:", resp.text)
        sys.exit(1)

    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_me(headers):
    resp = requests.get(f"{BASE_URL}/v1/users/me", headers=headers)
    if resp.status_code != 200:
        print("❌ Cannot fetch /me:", resp.text)
        sys.exit(1)
    return resp.json()


def print_service_stats(stats):
    print("🧠 Incremental LightGCN — SERVICE STATS")
    print("=" * 60)
    print(f"Time:                 {time.strftime('%H:%M:%S')}")
    print(f"Total users:          {stats.get('total_users', 0):,}")
    print(f"Base users:           {stats.get('base_users', 0):,}")
    print(f"New users created:    {stats.get('new_users_created', 0):,}")
    print(f"Total updates:        {stats.get('total_updates', 0):,} ⚡")
    print(f"Interactions since CP:{stats.get('interactions_since_checkpoint', 0):,}")
    print(f"Cache size:           {stats.get('cache_size')}")
    print(f"Embedding dim:        {stats.get('embedding_dim')}")
    print(f"Learning rate:        {stats.get('learning_rate')}")
    print(f"Incremental mode:     {'✅ ACTIVE' if stats.get('incremental_mode') else '❌ OFF'}")
    print("=" * 60)

    # Progress bar
    progress = stats.get("interactions_since_checkpoint", 0)
    max_cp = stats.get("checkpoint_interval", 1000)
    bar_width = 40
    filled = int(bar_width * min(progress, max_cp) / max_cp)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"Checkpoint: [{bar}] {progress}/{max_cp}")


def print_user_stats(stats, user):
    print("👤 Incremental LightGCN — USER STATS")
    print("=" * 60)
    print(f"Time:             {time.strftime('%H:%M:%S')}")
    print(f"User ID:          {user['_id']}")
    print(f"Email:            {user.get('email')}")
    print("-" * 60)
    print(f"Interactions:     {stats.get('interactions', 0)}")
    print(f"Embedding norm:   {stats.get('embedding_norm', 'N/A')}")
    print(f"Last update:      {stats.get('last_update', 'N/A')}")
    print("=" * 60)


def main():
    headers = login(USERNAME, PASSWORD)
    me = get_me(headers)

    role = me.get("role", "user")
    user_id = me["_id"]

    print(f"🔐 Logged as: {me.get('email')} ({role})")
    time.sleep(1)

    try:
        while True:
            clear_screen()

            if role == "admin":
                resp = requests.get(
                    f"{BASE_URL}/v1/recommendations/debug/service-stats", headers=headers
                )
                if resp.status_code == 200:
                    print_service_stats(resp.json())
                else:
                    print("❌ Service stats error:", resp.text)

            else:
                resp = requests.get(
                    f"{BASE_URL}/v1/recommendations/debug/user-stats/{user_id}", headers=headers
                )
                if resp.status_code == 200:
                    print_user_stats(resp.json(), me)
                else:
                    print("❌ User stats error:", resp.text)

            print("\nCtrl+C to stop monitoring…")
            time.sleep(REFRESH_SEC)

    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")


if __name__ == "__main__":
    main()
