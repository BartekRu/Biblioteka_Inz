"""
Enhanced Real-time Monitor for LightGCN + MongoDB Persistence
Shows: Service stats, User stats, MongoDB persistence, Embedding updates
"""

import requests
import time
import os
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

USERNAME = "admin"
PASSWORD = "admin123"
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


def get_health(headers):
    """Get recommendation service health"""
    try:
        resp = requests.get(f"{BASE_URL}/v1/recommendations/health", headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}


def get_embedding_info(user_id, headers):
    """Get user embedding diagnostics"""
    try:
        resp = requests.get(f"{BASE_URL}/v1/recommendations/user/embedding-info", headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}


def get_interaction_stats(headers):
    """Get interaction statistics from InteractionService"""
    try:
        resp = requests.get(f"{BASE_URL}/v1/stats", headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}


def print_header(title):
    """Print section header"""
    print("╔" + "═" * 78 + "╗")
    print(f"║ {title:^76} ║")
    print("╚" + "═" * 78 + "╝")


def print_service_stats(stats, health, interaction_stats):
    """Print comprehensive service statistics"""
    clear_screen()

    print_header("🧠 LIGHTGCN + MONGODB PERSISTENCE - SYSTEM MONITOR")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ Time: {current_time}\n")

    print("┌─ 🏥 SERVICE HEALTH " + "─" * 60 + "┐")

    status = health.get("status", "unknown")
    status_icon = "✅" if status == "healthy" else "⚠️" if status == "starting" else "❌"
    print(f"│ Status:                {status_icon} {status.upper():<30} │")
    print(f"│ Model loaded:          {'✅ YES' if health.get('model_loaded') else '❌ NO':<30} │")
    print(
        f"│ Incremental mode:      {'✅ ACTIVE' if health.get('incremental_mode') else '❌ OFF':<30} │"
    )
    print(f"│ MMR available:         {'✅ YES' if health.get('mmr_available') else '❌ NO':<30} │")
    print("└" + "─" * 78 + "┘\n")

    print("┌─ 📊 LIGHTGCN MODEL STATISTICS " + "─" * 48 + "┐")

    total_users = stats.get("total_users", 0)
    base_users = stats.get("base_users", 0)
    new_users = stats.get("new_users_created", 0)
    total_updates = stats.get("total_updates", 0)

    print(f"│ Total users in model:  {total_users:>10,}                                  │")
    print(f"│   ├─ Base users (trained):  {base_users:>10,}                             │")
    print(f"│   └─ New users (incremental): {new_users:>10,}                            │")
    print(f"│                                                                              │")
    print(f"│ Total embedding updates: {total_updates:>10,} ⚡                            │")
    print(
        f"│ Updates since checkpoint: {stats.get('interactions_since_checkpoint', 0):>10,}                           │"
    )
    print(f"│                                                                              │")
    print(
        f"│ Embedding dimension:   {stats.get('embedding_dim', 'N/A'):>10}                                   │"
    )
    print(
        f"│ Learning rate:         {stats.get('learning_rate', 'N/A'):>10}                                   │"
    )
    print(
        f"│ Cache size:            {stats.get('cache_size', 'N/A'):>10}                                   │"
    )
    print("└" + "─" * 78 + "┘\n")

    progress = stats.get("interactions_since_checkpoint", 0)
    max_cp = stats.get("checkpoint_interval", 1000)
    if max_cp > 0:
        bar_width = 60
        filled = int(bar_width * min(progress, max_cp) / max_cp)
        bar = "█" * filled + "░" * (bar_width - filled)
        percentage = min(100, int(100 * progress / max_cp))
        print(f"┌─ CHECKPOINT PROGRESS " + "─" * 56 + "┐")
        print(f"│ [{bar}] {percentage:>3}% │")
        print(
            f"│ {progress:,} / {max_cp:,} interactions                                              │"
        )
        print("└" + "─" * 78 + "┘\n")

    interactions = interaction_stats.get("interactions", {})
    embeddings = interaction_stats.get("embeddings", {})

    print("┌─ 💾 MONGODB PERSISTENCE " + "─" * 53 + "┐")

    total_interactions = interactions.get("total", 0)
    embeddings_updated = embeddings.get("embeddings_updated", 0)
    update_rate = embeddings.get("update_rate", 0)

    print(f"│ Total interactions:    {total_interactions:>10,}                                  │")
    print(
        f"│   ├─ view:             {interactions.get('view', 0):>10,}                                  │"
    )
    print(
        f"│   ├─ review:           {interactions.get('review', 0):>10,}                                  │"
    )
    print(
        f"│   └─ borrow:           {interactions.get('borrow', 0):>10,}                                  │"
    )
    print(f"│                                                                              │")
    print(f"│ Embeddings persisted:  {embeddings_updated:>10,}                                  │")

    if update_rate >= 80:
        rate_icon = "🟢"
    elif update_rate >= 50:
        rate_icon = "🟡"
    else:
        rate_icon = "🔴"

    print(
        f"│ Persistence rate:      {rate_icon} {update_rate:>6.1f}%                                     │"
    )

    if total_interactions > 0:
        bar_width = 60
        filled = int(bar_width * embeddings_updated / total_interactions)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"│ [{bar}]      │")

    print("└" + "─" * 78 + "┘\n")


def print_user_stats(stats, user, embedding_info, interaction_stats):
    clear_screen()

    print_header("👤 USER PROFILE - EMBEDDING & INTERACTION TRACKING")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ Time: {current_time}\n")

    print("┌─ 👤 USER IDENTITY " + "─" * 59 + "┐")
    print(f"│ User ID:    {user['_id']:<62} │")
    print(f"│ Email:      {user.get('email', 'N/A'):<62} │")
    print(f"│ Role:       {user.get('role', 'user'):<62} │")
    print("└" + "─" * 78 + "┘\n")

    print("┌─ 🧠 EMBEDDING STATUS " + "─" * 56 + "┐")

    has_model = embedding_info.get("has_model_index", False)
    has_mongo = embedding_info.get("has_mongodb_embedding", False)
    is_cold_start = embedding_info.get("is_cold_start", True)

    model_icon = "✅" if has_model else "❌"
    mongo_icon = "✅" if has_mongo else "❌"
    cold_icon = "❄️" if is_cold_start else "🔥"

    print(f"│ In LightGCN model:     {model_icon} {'YES' if has_model else 'NO':<40} │")
    if has_model:
        print(f"│   Model index:         {embedding_info.get('model_index', 'N/A'):<50} │")

    print(f"│ MongoDB embedding:     {mongo_icon} {'YES' if has_mongo else 'NO':<40} │")
    if has_mongo:
        last_updated = embedding_info.get("embedding_last_updated", "Never")
        if last_updated and last_updated != "Never":
            try:
                dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                last_updated = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        print(f"│   Last updated:        {last_updated:<50} │")

    print(f"│                                                                              │")
    print(
        f"│ Status:                {cold_icon} {'COLD-START' if is_cold_start else 'PERSONALIZED':<40} │"
    )

    recommendation = embedding_info.get("recommendation", "")
    if recommendation:
        import textwrap

        wrapped = textwrap.wrap(recommendation, width=62)
        print(f"│ Recommendation:        {wrapped[0] if wrapped else '':<50} │")
        for line in wrapped[1:]:
            print(f"│                        {line:<50} │")

    print("└" + "─" * 78 + "┘\n")

    print("┌─ 📊 INTERACTION STATISTICS " + "─" * 50 + "┐")

    total_interactions = embedding_info.get("interaction_count_actual", 0)
    embeddings_updated = embedding_info.get("embeddings_updated_count", 0)

    print(f"│ Total interactions:    {total_interactions:>10,}                                  │")
    print(f"│ Embeddings updated:    {embeddings_updated:>10,}                                  │")

    if total_interactions > 0:
        update_rate = (embeddings_updated / total_interactions) * 100
        if update_rate >= 80:
            rate_icon = "🟢"
        elif update_rate >= 50:
            rate_icon = "🟡"
        else:
            rate_icon = "🔴"

        print(
            f"│ Update rate:           {rate_icon} {update_rate:>6.1f}%                                     │"
        )

        bar_width = 60
        filled = int(bar_width * embeddings_updated / total_interactions)
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"│ [{bar}]      │")

    print("└" + "─" * 78 + "┘\n")

    print("┌─ 📈 EMBEDDING QUALITY " + "─" * 55 + "┐")

    norm = stats.get("embedding_norm", "N/A")
    if isinstance(norm, float):
        if norm > 0.5:
            quality = "🟢 Good"
        elif norm > 0.1:
            quality = "🟡 Fair"
        else:
            quality = "🔴 Weak"

        print(f"│ Embedding norm:        {norm:.6f}                                      │")
        print(f"│ Quality:               {quality:<50} │")
    else:
        print(f"│ Embedding norm:        {norm:<50} │")
        print(f"│ Quality:               N/A - Need more interactions                      │")

    print(f"│                                                                              │")

    mongo_count = embedding_info.get("interaction_count_mongodb", 0)
    if mongo_count > 0:
        print(f"│ MongoDB interactions:  {mongo_count:>10,}                                  │")
        sync_status = "✅ Synced" if mongo_count == total_interactions else "⚠️ Out of sync"
        print(f"│ Sync status:           {sync_status:<50} │")

    print("└" + "─" * 78 + "┘\n")

    print("┌─ 🎯 RECOMMENDATIONS " + "─" * 57 + "┐")

    if is_cold_start:
        strategy = "Hybrid (60% LightGCN + 40% Content-based)"
        print(f"│ Strategy:              ❄️  {strategy:<45} │")
        print(f"│ Status:                Collecting preferences...                         │")
        needed = 5 - total_interactions
        if needed > 0:
            print(
                f"│ Actions needed:        {needed} more interactions for full personalization      │"
            )
    else:
        strategy = "LightGCN Collaborative Filtering"
        print(f"│ Strategy:              🔥 {strategy:<45} │")
        print(f"│ Status:                Fully personalized                                 │")
        print(
            f"│ Quality:               Excellent - based on {total_interactions} interactions                │"
        )

    print("└" + "─" * 78 + "┘\n")


def main():
    print("🔐 Logging in...")
    headers = login(USERNAME, PASSWORD)
    me = get_me(headers)

    role = me.get("role", "user")
    user_id = me["_id"]

    print(f"✅ Logged in as: {me.get('email')} ({role})")
    print(f"🔄 Starting monitor (refresh every {REFRESH_SEC}s)...\n")
    time.sleep(2)

    try:
        while True:
            health = get_health(headers)

            interaction_stats = get_interaction_stats(headers)

            if role == "admin":
                resp = requests.get(
                    f"{BASE_URL}/v1/recommendations/debug/service-stats", headers=headers
                )
                if resp.status_code == 200:
                    service_stats = resp.json()
                    print_service_stats(service_stats, health, interaction_stats)
                else:
                    print("❌ Service stats error:", resp.text)

            else:
                resp = requests.get(
                    f"{BASE_URL}/v1/recommendations/debug/user-stats/{user_id}", headers=headers
                )

                embedding_info = get_embedding_info(user_id, headers)

                if resp.status_code == 200:
                    user_stats = resp.json()
                    print_user_stats(user_stats, me, embedding_info, interaction_stats)
                else:
                    print("❌ User stats error:", resp.text)

            print("\n" + "─" * 78)
            print(f"🔄 Auto-refresh in {REFRESH_SEC}s | Press Ctrl+C to stop")
            print("─" * 78)

            time.sleep(REFRESH_SEC)

    except KeyboardInterrupt:
        print("\n\n" + "═" * 78)
        print("👋 Monitoring stopped - Goodbye!")
        print("═" * 78)


if __name__ == "__main__":
    main()
