import pandas as pd
import numpy as np
from collections import defaultdict
import json

# Załaduj ratings
print("Ładowanie ratings.csv...")
df = pd.read_csv('goodbooks-10k/ratings.csv')
print(f"Załadowano {len(df):,} ocen")

# Filtruj użytkowników i książki z min. 5 interakcjami
min_interactions = 5
for _ in range(3):
    user_counts = df['user_id'].value_counts()
    valid_users = user_counts[user_counts >= min_interactions].index
    df = df[df['user_id'].isin(valid_users)]
    
    book_counts = df['book_id'].value_counts()
    valid_books = book_counts[book_counts >= min_interactions].index
    df = df[df['book_id'].isin(valid_books)]

print(f"Po filtracji: {len(df):,} ocen")

# Stwórz mapowania na ciągłe ID (0 do N-1)
unique_users = sorted(df['user_id'].unique())
unique_books = sorted(df['book_id'].unique())

user_to_idx = {u: i for i, u in enumerate(unique_users)}
book_to_idx = {b: i for i, b in enumerate(unique_books)}

print(f"Użytkownicy: {len(user_to_idx):,}")
print(f"Książki: {len(book_to_idx):,}")

# Grupuj po użytkowniku
user_items = df.groupby('user_id')['book_id'].apply(list).to_dict()

# Podziel na train/test (80/20)
np.random.seed(2024)
train_data = []
test_data = []

for user_id, items in user_items.items():
    n_test = max(1, int(len(items) * 0.2))
    indices = np.random.permutation(len(items))
    
    test_items = [items[i] for i in indices[:n_test]]
    train_items = [items[i] for i in indices[n_test:]]
    
    if train_items:
        train_data.append((user_id, train_items))
        if test_items:
            test_data.append((user_id, test_items))

# Zapisz w formacie LightGCN: user_id item1 item2 item3...
def save_lightgcn_format(data, filename):
    with open(f'processed/{filename}', 'w') as f:
        for user_id, items in data:
            user_idx = user_to_idx[user_id]
            item_indices = [str(book_to_idx[item]) for item in items]
            f.write(f"{user_idx} {' '.join(item_indices)}\n")

save_lightgcn_format(train_data, 'train.txt')
save_lightgcn_format(test_data, 'test.txt')

# Zapisz mapowania - konwertuj numpy int64 na zwykły int
with open('processed/user_mapping.json', 'w') as f:
    json.dump({
        'to_idx': {int(k): int(v) for k, v in user_to_idx.items()}, 
        'to_original': {int(v): int(k) for k, v in user_to_idx.items()}
    }, f)

with open('processed/book_mapping.json', 'w') as f:
    json.dump({
        'to_idx': {int(k): int(v) for k, v in book_to_idx.items()}, 
        'to_original': {int(v): int(k) for k, v in book_to_idx.items()}
    }, f)

print("✅ Dane zapisane w data/processed/")