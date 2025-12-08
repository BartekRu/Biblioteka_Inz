import asyncio
import json
from pathlib import Path
from typing import List, Tuple, Dict

from bson import ObjectId

from app.database import get_database, connect_to_mongo



DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


async def load_interactions() -> List[Tuple[str, str]]:
    """
    Zbiera interakcje z:
    - kolekcji `interactions`
    - kolekcji `loans` (traktowane jako 'borrow')
    Zwraca listę (user_id_str, book_id_str).
    """
    db = get_database()
    interactions: List[Tuple[str, str]] = []

    # 1) interactions
    async for doc in db.interactions.find({}):
        uid = doc.get("user_id")
        bid = doc.get("book_id")
        if not uid or not bid:
            continue
        interactions.append((str(uid), str(bid)))

    # 2) loans jako dodatkowe 'borrow'
    async for loan in db.loans.find({}):
        uid = loan.get("user_id")
        bid = loan.get("book_id")
        if not uid or not bid:
            continue
        interactions.append((str(uid), str(bid)))

    # usuwamy duplikaty
    interactions = list(set(interactions))
    return interactions


def build_index_mapping(
    interactions: List[Tuple[str, str]]
) -> Tuple[List[Tuple[int, int]], Dict[str, int], Dict[str, int]]:
    """
    Robi mapowanie:
    - user_id (string)  -> user_idx (int)
    - book_id (string)  -> item_idx (int)
    Zwraca:
    - listę (user_idx, item_idx)
    - słownik user_mapping
    - słownik item_mapping
    """
    user_mapping: Dict[str, int] = {}
    item_mapping: Dict[str, int] = {}

    next_user_idx = 0
    next_item_idx = 0

    indexed_pairs: List[Tuple[int, int]] = []

    for user_id, book_id in interactions:
        if user_id not in user_mapping:
            user_mapping[user_id] = next_user_idx
            next_user_idx += 1

        if book_id not in item_mapping:
            item_mapping[book_id] = next_item_idx
            next_item_idx += 1

        u_idx = user_mapping[user_id]
        i_idx = item_mapping[book_id]
        indexed_pairs.append((u_idx, i_idx))

    return indexed_pairs, user_mapping, item_mapping


def save_dataset(
    pairs: List[Tuple[int, int]],
    user_mapping: Dict[str, int],
    item_mapping: Dict[str, int],
):
    """
    Zapisuje:
    - data/lightgcn_train.txt       (user_idx item_idx)
    - data/user_mapping.json        (user_id -> idx)
    - data/item_mapping.json        (book_id -> idx)
    """
    train_path = DATA_DIR / "lightgcn_train.txt"
    users_path = DATA_DIR / "user_mapping.json"
    items_path = DATA_DIR / "item_mapping.json"

    # plik z interakcjami
    with train_path.open("w", encoding="utf-8") as f:
        for u_idx, i_idx in pairs:
            f.write(f"{u_idx} {i_idx}\n")

    # mapowania
    with users_path.open("w", encoding="utf-8") as f:
        json.dump(user_mapping, f)

    with items_path.open("w", encoding="utf-8") as f:
        json.dump(item_mapping, f)

    print(f"Zapisano {len(pairs)} interakcji do {train_path}")
    print(f"Użytkownicy: {len(user_mapping)}, książki: {len(item_mapping)}")


async def main():
    await connect_to_mongo()
    interactions = await load_interactions()
    print(f"Pobrano {len(interactions)} surowych interakcji")

    if not interactions:
        print("Brak interakcji – nie ma co trenować 😅")
        return

    pairs, user_mapping, item_mapping = build_index_mapping(interactions)
    save_dataset(pairs, user_mapping, item_mapping)


if __name__ == "__main__":
    asyncio.run(main())
