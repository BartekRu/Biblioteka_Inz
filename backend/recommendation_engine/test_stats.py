import requests
import json

# 1. Login
print("🔐 Logowanie...")
login_response = requests.post(
    "http://localhost:8000/v1/auth/token",
    data={"username": "admin", "password": "admin123"},  # ← ZMIEŃ NA SWOJE HASŁO!
)

if login_response.status_code != 200:
    print(f"❌ Błąd logowania: {login_response.text}")
    exit(1)

token = login_response.json()["access_token"]
print(f"✅ Token otrzymany: {token[:30]}...")


# 2. Get stats
print("\n📊 Pobieranie statystyk...")
headers = {"Authorization": f"Bearer {token}"}
# stats_response = requests.get(
#     "http://localhost:8000/v1/recommendations/debug/service-stats",
#     headers=headers
# )

user_id = "6944219d5cc2ae30cfe2afdc"
stats_response = requests.get(
    f"http://localhost:8000/v1/recommendations/debug/user-stats/{user_id}", headers=headers
)


if stats_response.status_code != 200:
    print(f"❌ Błąd: {stats_response.text}")
    exit(1)

# 3. Wyświetl ładnie
stats = stats_response.json()
print("\n🔍 RAW RESPONSE:")
print(json.dumps(stats, indent=2, ensure_ascii=False))
print("\n✨ Statystyki Incremental LightGCN:")
print("\n✨ Statystyki użytkownika (LightGCN):")
print("=" * 50)
print(f"User ID:          {stats.get('user_id')}")
print(f"Interactions:     {stats.get('interactions', 0)}")
print(f"Embedding norm:   {stats.get('embedding_norm', 'N/A')}")
print(f"Last update:      {stats.get('last_update', 'N/A')}")
print("=" * 50)

# print("=" * 50)
# print(f"Base users:           {stats['base_users']:,}")
# print(f"Total users:          {stats['total_users']:,}")
# print(f"New users created:    {stats['new_users_created']:,}")
# print(f"Total items:          {stats['total_items']:,}")
# print(f"Total updates:        {stats['total_updates']:,}")
# print(f"Since checkpoint:     {stats['interactions_since_checkpoint']:,}")
# print(f"Cache size:           {stats['cache_size']}")
# print(f"Embedding dim:        {stats['embedding_dim']}")
# print(f"Learning rate:        {stats['learning_rate']}")
# print(f"Incremental mode:     {stats['incremental_mode']}")
print("=" * 50)

# 4. Sprawdź czy działa
# if stats['total_updates'] > 0:
#     print("\n🎉 System działa! Embeddingi są aktualizowane!")
# else:
#     print("\n⚠️  Brak updates - sprawdź czy są interakcje")
