import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm
import matplotlib.pyplot as plt
from collections import defaultdict


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

DATA_DIR = "recommendation_engine/data/goodbooks_data"
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.csv")

MODEL_DIR = "recommendation_engine/model"
os.makedirs(MODEL_DIR, exist_ok=True)

# HYPERPARAMETERS (PRO)
EMBEDDING_DIM = 128
LAYERS = 3
EPOCHS = 60
LR = 0.001
BATCH_SIZE = 4096
NEGATIVE_SAMPLES = 1


# ============================================================
#                   LIGHTGCN MODEL (PRO)
# ============================================================
class LightGCN(nn.Module):
    """
    Zgodna z artykułem: 'LightGCN – Simplifying Graph Convolution Network
    for Recommendation' (He et al., 2020).
    """
    def __init__(self, num_users, num_items):
        super().__init__()
        self.num_users = num_users
        self.num_items = num_items
        self.num_nodes = num_users + num_items

        self.embedding = nn.Embedding(self.num_nodes, EMBEDDING_DIM)
        nn.init.xavier_uniform_(self.embedding.weight)

        # warstwy propagacji zgodne z LightGCN
        self.layers = LAYERS

    def propagate(self, edge_index):
    
        x = self.embedding.weight  # [num_nodes, emb_dim]
        embs = [x]

        rows = edge_index[0]
        cols = edge_index[1]

        # degree d(i)
        deg = torch.bincount(rows, minlength=self.num_nodes).float()
        deg_inv_sqrt = deg.pow(-0.5)
        deg_inv_sqrt[deg_inv_sqrt == float("inf")] = 0

        deg_inv_sqrt_rows = deg_inv_sqrt[rows].unsqueeze(1)
        deg_inv_sqrt_cols = deg_inv_sqrt.unsqueeze(1)

        for _ in range(self.layers):
            # wiadomość od u -> v (normalizowana)
            msg = x[rows] * deg_inv_sqrt_rows  # [E, emb_dim]

            # agregacja na node-ach
            agg = torch.zeros_like(x)
            agg.index_add_(0, cols, msg)

            # D^-1/2 z prawej strony
            x = agg * deg_inv_sqrt_cols  # [num_nodes, emb_dim]

            embs.append(x)

        out = torch.stack(embs, dim=0).mean(0)
        return out.split([self.num_users, self.num_items])



    def forward(self, users, pos_items, neg_items, edge_index):
        users_emb, items_emb = self.propagate(edge_index)

        u = users_emb[users]
        pos = items_emb[pos_items]
        neg = items_emb[neg_items]

        pos_score = torch.sum(u * pos, dim=1)
        neg_score = torch.sum(u * neg, dim=1)

        loss = -torch.mean(torch.log(torch.sigmoid(pos_score - neg_score)))
        return loss


# ============================================================
#                     Wczytywanie GOODBOOKS
# ============================================================
def load_goodbooks():
    print(f"📥 Wczytuję dane z {RATINGS_FILE}")
    df = pd.read_csv(RATINGS_FILE)

    # rating >= 3 → implicit positive
    df = df[df["rating"] >= 3]

    print(f"✔ Pozytywnych interakcji: {len(df)}")

    user_idx = df["user_id"].astype("category").cat.codes
    item_idx = df["book_id"].astype("category").cat.codes

    df["user_idx"] = user_idx
    df["item_idx"] = item_idx

    num_users = user_idx.max() + 1
    num_items = item_idx.max() + 1

    print(f"✔ Użytkownicy: {num_users}, Książki: {num_items}")

    return df, num_users, num_items


# ============================================================
#                    Negative Sampler
# ============================================================
class NegativeSampler:
    def __init__(self, num_items):
        self.num_items = num_items

    def sample(self, batch_size):
        return torch.randint(0, self.num_items, (batch_size,), device=DEVICE)
# ============================================================
#               Budowa edge_index do propagacji
# ============================================================
def build_edge_index(df, num_users):
    """
    Tworzy listę krawędzi (user, item+offset) oraz lustro (item+offset, user)
    zgodnie z dwukierunkowym grafem LightGCN.
    """
    users = torch.tensor(df["user_idx"].values, dtype=torch.long, device=DEVICE)
    items = torch.tensor(df["item_idx"].values, dtype=torch.long, device=DEVICE) + num_users

    # BIPARTITE GRAPH EDGES:
    # u -> i
    # i -> u  (bo graf bezkierunkowy)
    rows = torch.cat([users, items])
    cols = torch.cat([items, users])

    return torch.stack([rows, cols], dim=0)


# ============================================================
#                  Ewaluacja Recall@20 / NDCG@20
# ============================================================
def evaluate(model, edge_index, df, num_users, num_items, sample_users=2000):
    """
    Eval na zestawie użytkowników (domyślnie 2000 losowych).
    LightGCN: ranking wszystkich itemów i liczenie Recall/NDCG.
    """
    print("🔍 Ewaluacja modelu...")

    # wybór użytkowników
    users = np.random.choice(num_users, sample_users, replace=False)

    # mapowanie: user -> list of positives
    positives = defaultdict(list)
    for u, i in zip(df["user_idx"], df["item_idx"]):
        positives[u].append(i)

    model.eval()
    with torch.no_grad():
        users_emb, items_emb = model.propagate(edge_index)

    recall_list = []
    ndcg_list = []

    for u in users:
        if len(positives[u]) == 0:
            continue

        user_emb = users_emb[u]
        scores = torch.matmul(user_emb, items_emb.T)
        _, ranked_items = torch.topk(scores, 20)

        ranked_items = ranked_items.cpu().numpy()
        pos = set(positives[u])

        # Recall@20
        hit_count = sum([1 for x in ranked_items if x in pos])
        recall = hit_count / len(pos)
        recall_list.append(recall)

        # NDCG@20
        dcg = 0.0
        for idx, item in enumerate(ranked_items):
            if item in pos:
                dcg += 1.0 / np.log2(idx + 2)
        idcg = sum([1.0 / np.log2(i + 2) for i in range(min(len(pos), 20))])
        ndcg = dcg / idcg if idcg > 0 else 0.0
        ndcg_list.append(ndcg)

    return float(np.mean(recall_list)), float(np.mean(ndcg_list))


# ============================================================
#              GŁÓWNA PĘTLA TRENINGOWA (PRO)
# ============================================================
def train():
    df, num_users, num_items = load_goodbooks()

    # edge index
    edge_index = build_edge_index(df, num_users)

    # model
    model = LightGCN(num_users, num_items).to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=LR)
    neg_sampler = NegativeSampler(num_items)

    # konwersja tensorów
    user_tensor = torch.tensor(df["user_idx"].values, dtype=torch.long, device=DEVICE)
    item_tensor = torch.tensor(df["item_idx"].values, dtype=torch.long, device=DEVICE)

    # statystyki do wykresów
    losses = []
    recalls = []
    ndcgs = []
    epochs_logged = []

    print("\n🚀 Start treningu PRO LightGCN\n")

    for epoch in range(1, EPOCHS + 1):
        model.train()
        perm = torch.randperm(len(df), device=DEVICE)
        u_shuffled = user_tensor[perm]
        p_shuffled = item_tensor[perm]

        epoch_losses = []

        for i in range(0, len(df), BATCH_SIZE):
            users = u_shuffled[i:i+BATCH_SIZE]
            pos_items = p_shuffled[i:i+BATCH_SIZE]
            neg_items = neg_sampler.sample(len(users))

            optimizer.zero_grad()
            loss = model(users, pos_items, neg_items, edge_index)
            loss.backward()
            optimizer.step()

            epoch_losses.append(loss.item())

        mean_loss = np.mean(epoch_losses)
        losses.append(mean_loss)

        print(f"Epoch {epoch}/{EPOCHS} | Loss: {mean_loss:.4f}")

        # co 5 epok — ewaluacja
        if epoch % 5 == 0:
            recall20, ndcg20 = evaluate(model, edge_index, df, num_users, num_items)
            recalls.append(recall20)
            ndcgs.append(ndcg20)
            epochs_logged.append(epoch)

            print(f"📊 Recall@20: {recall20:.4f}")
            print(f"📊 NDCG@20:  {ndcg20:.4f}\n")

    # zapis modelu
    save_path = os.path.join(MODEL_DIR, "lightgcn_goodbooks_pro.pt")
    torch.save(model.state_dict(), save_path)
    print(f"🎉 Model zapisany do {save_path}")

    return losses, recalls, ndcgs, epochs_logged, num_users, num_items, df, edge_index
# ============================================================
#                    GENEROWANIE WYKRESÓW
# ============================================================
def plot_training(losses, recalls, ndcgs, epochs_logged):
    os.makedirs("recommendation_engine/plots", exist_ok=True)

    # ---------- LOSS ----------
    plt.figure(figsize=(8,5))
    plt.plot(losses, label="Loss")
    plt.xlabel("Epoka")
    plt.ylabel("Loss")
    plt.title("LightGCN — Loss per epoch")
    plt.grid(True, alpha=0.3)
    plt.savefig("recommendation_engine/plots/loss_curve.png")
    plt.close()

    # ---------- RECALL ----------
    plt.figure(figsize=(8,5))
    plt.plot(epochs_logged, recalls, marker="o", label="Recall@20")
    plt.xlabel("Epoka")
    plt.ylabel("Recall@20")
    plt.title("LightGCN — Recall@20 co 5 epok")
    plt.grid(True, alpha=0.3)
    plt.savefig("recommendation_engine/plots/recall_curve.png")
    plt.close()

    # ---------- NDCG ----------
    plt.figure(figsize=(8,5))
    plt.plot(epochs_logged, ndcgs, marker="o", color="orange", label="NDCG@20")
    plt.xlabel("Epoka")
    plt.ylabel("NDCG@20")
    plt.title("LightGCN — NDCG@20 co 5 epok")
    plt.grid(True, alpha=0.3)
    plt.savefig("recommendation_engine/plots/ndcg_curve.png")
    plt.close()

    print("📊 Wykresy zapisane w: recommendation_engine/plots/")


# ============================================================
#                           MAIN
# ============================================================
if __name__ == "__main__":
    print(f"🚀 Start treningu LightGCN PRO (device={DEVICE})")

    losses, recalls, ndcgs, epochs_logged, num_users, num_items, df, edge_index = train()

    # Eval końcowy na pełnych danych
    print("🏁 Końcowa ewaluacja na 2000 użytkownikach...")
    final_recall20, final_ndcg20 = evaluate(
        LightGCN(num_users, num_items).to(DEVICE),
        edge_index,
        df,
        num_users,
        num_items,
        sample_users=2000
    )

    print(f"\n📌 Final Recall@20: {final_recall20:.4f}")
    print(f"📌 Final NDCG@20:  {final_ndcg20:.4f}")

    # zapis wykresów
    plot_training(losses, recalls, ndcgs, epochs_logged)

    # zapis metryk do JSON
    metrics_path = os.path.join(MODEL_DIR, "lightgcn_goodbooks_pro_metrics.json")
    metrics = {
        "recall20": float(final_recall20),
        "ndcg20": float(final_ndcg20),
        "epochs": EPOCHS,
        "embeddingDim": EMBEDDING_DIM,
        "layers": LAYERS,
        "learningRate": LR,
        "interactions_used": len(df),
        "dataset": "goodbooks-10k",
        "coverage": float(len(set(df['item_idx'])) / num_items),
    }

    import json
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)

    print(f"📁 Metryki zapisane do {metrics_path}")
    print("\n🎉 Trening LightGCN PRO zakończony!\n")
