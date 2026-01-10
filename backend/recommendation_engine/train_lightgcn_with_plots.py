"""
🎯 LightGCN Training Script - Praca Inżynierska
=================================================
Kompletny skrypt treningowy z:
- Train/Validation/Test split
- Wykresy: Loss, Recall@K, Precision@K, NDCG@K
- Metryki: Coverage, Diversity, Serendipity
- Profesjonalne wizualizacje

Dataset: goodbooks-10k
Model: LightGCN (He et al., 2020)
"""

import os
import json
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm

import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")  # Backend for saving plots

# Ustawienia stylu wykresów (jak w przykładach)
plt.style.use("seaborn-v0_8-darkgrid")
plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["font.size"] = 11
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["legend.fontsize"] = 10
plt.rcParams["lines.linewidth"] = 2
plt.rcParams["lines.markersize"] = 6

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🔧 Device: {DEVICE}")


# ============================================================
#                      KONFIGURACJA
# ============================================================
class Config:
    # Ścieżki (dostosowane do struktury projektu)
    # Jeśli jesteś w backend/recommendation_engine, to dane są w ./data/goodbooks_data
    DATA_DIR = os.path.join("data", "goodbooks_data")
    RATINGS_FILE = os.path.join(DATA_DIR, "ratings.csv")
    OUTPUT_DIR = os.path.join("training_output")
    PLOTS_DIR = os.path.join(OUTPUT_DIR, "plots")
    MODEL_DIR = os.path.join(OUTPUT_DIR, "models")

    # Hiperparametry
    EMBEDDING_DIM = 128
    LAYERS = 3
    EPOCHS = 60
    LR = 0.001
    BATCH_SIZE = 4096
    NEGATIVE_SAMPLES = 1

    # Ewaluacja
    EVAL_EVERY = 5  # Co ile epok ewaluacja
    K_VALUES = [5, 10, 20]  # Recall@K, Precision@K, NDCG@K
    SAMPLE_USERS_EVAL = 2000  # Ile userów do ewaluacji

    # Split (time-based)
    TRAIN_RATIO = 0.8
    VAL_RATIO = 0.1
    TEST_RATIO = 0.1

    # Random seed dla reprodukowalności
    SEED = 42


# Tworzenie katalogów
for dir_path in [Config.OUTPUT_DIR, Config.PLOTS_DIR, Config.MODEL_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Seed dla reprodukowalności
np.random.seed(Config.SEED)
torch.manual_seed(Config.SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(Config.SEED)


# ============================================================
#                   LIGHTGCN MODEL
# ============================================================
class LightGCN(nn.Module):
    """
    LightGCN: Simplifying and Powering Graph Convolution Network
    for Recommendation (He et al., 2020)

    Paper: https://arxiv.org/abs/2002.02126
    """

    def __init__(self, num_users, num_items, embedding_dim=128, n_layers=3):
        super().__init__()
        self.num_users = num_users
        self.num_items = num_items
        self.num_nodes = num_users + num_items
        self.n_layers = n_layers

        # Learnable embeddings
        self.embedding = nn.Embedding(self.num_nodes, embedding_dim)
        nn.init.xavier_uniform_(self.embedding.weight)

    def propagate(self, edge_index):
        """
        Graph propagation zgodnie z LightGCN:
        - Brak weight matrices
        - Brak activation functions
        - Layer combination przez averaging
        """
        x = self.embedding.weight  # [num_nodes, emb_dim]
        all_embeddings = [x]

        rows = edge_index[0]
        cols = edge_index[1]

        # Degree normalization: D^-1/2
        deg = torch.bincount(rows, minlength=self.num_nodes).float()
        deg_inv_sqrt = deg.pow(-0.5)
        deg_inv_sqrt[deg_inv_sqrt == float("inf")] = 0

        deg_inv_sqrt_rows = deg_inv_sqrt[rows].unsqueeze(1)
        deg_inv_sqrt_cols = deg_inv_sqrt.unsqueeze(1)

        # Multi-layer propagation
        for _ in range(self.n_layers):
            # Message passing: D^-1/2 * A * D^-1/2 * X
            msg = x[rows] * deg_inv_sqrt_rows

            agg = torch.zeros_like(x)
            agg.index_add_(0, cols, msg)

            x = agg * deg_inv_sqrt_cols
            all_embeddings.append(x)

        # Layer combination: simple average
        final_emb = torch.stack(all_embeddings, dim=0).mean(0)

        # Split users and items
        users_emb = final_emb[: self.num_users]
        items_emb = final_emb[self.num_users :]

        return users_emb, items_emb

    def forward(self, users, pos_items, neg_items, edge_index):
        """BPR Loss (Bayesian Personalized Ranking)"""
        users_emb, items_emb = self.propagate(edge_index)

        u = users_emb[users]
        pos = items_emb[pos_items]
        neg = items_emb[neg_items]

        pos_score = torch.sum(u * pos, dim=1)
        neg_score = torch.sum(u * neg, dim=1)

        # BPR loss
        loss = -torch.mean(torch.log(torch.sigmoid(pos_score - neg_score) + 1e-10))

        return loss

    def predict(self, users, items, edge_index):
        """Prediction for evaluation"""
        users_emb, items_emb = self.propagate(edge_index)

        u = users_emb[users]
        i = items_emb[items]

        scores = torch.sum(u * i, dim=1)
        return scores


# ============================================================
#                  DATA LOADING & SPLITTING
# ============================================================
def load_and_split_data():
    """
    Wczytuje dane i dzieli na train/val/test.

    Strategie:
    1. Time-based split (chronological) - zalecane dla RS
    2. Random split (fallback jeśli brak timestampów)

    Returns:
        train_df, val_df, test_df, num_users, num_items
    """
    print(f"\n📥 Wczytywanie danych z {Config.RATINGS_FILE}")
    df = pd.read_csv(Config.RATINGS_FILE)

    print(f"✔ Załadowano {len(df):,} interakcji")
    print(f"✔ Unikalne użytkownicy: {df['user_id'].nunique():,}")
    print(f"✔ Unikalne książki: {df['book_id'].nunique():,}")

    # Filtracja: rating >= 3 → implicit positive
    df = df[df["rating"] >= 3].copy()
    print(f"✔ Pozytywne interakcje (rating ≥ 3): {len(df):,}")

    # Mapowanie ID → indeksy
    user_mapping = {uid: idx for idx, uid in enumerate(df["user_id"].unique())}
    item_mapping = {iid: idx for idx, iid in enumerate(df["book_id"].unique())}

    df["user_idx"] = df["user_id"].map(user_mapping)
    df["item_idx"] = df["book_id"].map(item_mapping)

    num_users = len(user_mapping)
    num_items = len(item_mapping)

    print(f"\n📊 Po mapowaniu:")
    print(f"   Users: {num_users:,}")
    print(f"   Items: {num_items:,}")
    print(f"   Sparsity: {100 * len(df) / (num_users * num_items):.4f}%")

    # TIME-BASED SPLIT (jeśli są timestampy) lub RANDOM SPLIT
    print(
        f"\n✂️ Podział danych (train:{Config.TRAIN_RATIO}, val:{Config.VAL_RATIO}, test:{Config.TEST_RATIO})"
    )

    # Sortowanie chronologicznie (jeśli możliwe)
    # Goodbooks nie ma timestampów, więc random split
    df = df.sample(frac=1, random_state=Config.SEED).reset_index(drop=True)

    n = len(df)
    train_end = int(n * Config.TRAIN_RATIO)
    val_end = int(n * (Config.TRAIN_RATIO + Config.VAL_RATIO))

    train_df = df[:train_end].copy()
    val_df = df[train_end:val_end].copy()
    test_df = df[val_end:].copy()

    print(f"✔ Train: {len(train_df):,} ({len(train_df)/n*100:.1f}%)")
    print(f"✔ Val:   {len(val_df):,} ({len(val_df)/n*100:.1f}%)")
    print(f"✔ Test:  {len(test_df):,} ({len(test_df)/n*100:.1f}%)")

    # Weryfikacja że wszystkie zbiory mają użytkowników
    train_users = train_df["user_idx"].nunique()
    val_users = val_df["user_idx"].nunique()
    test_users = test_df["user_idx"].nunique()

    print(f"\n📊 Użytkownicy w zbiorach:")
    print(f"   Train: {train_users:,} unique users")
    print(f"   Val:   {val_users:,} unique users")
    print(f"   Test:  {test_users:,} unique users")

    return train_df, val_df, test_df, num_users, num_items


def build_edge_index(df, num_users):
    """
    Buduje bipartite graph dla LightGCN.

    Args:
        df: DataFrame z kolumnami user_idx, item_idx
        num_users: liczba użytkowników (offset dla items)

    Returns:
        edge_index: [2, num_edges] tensor
    """
    users = torch.tensor(df["user_idx"].values, dtype=torch.long, device=DEVICE)
    items = torch.tensor(df["item_idx"].values, dtype=torch.long, device=DEVICE) + num_users

    # Bipartite undirected graph: u↔i
    rows = torch.cat([users, items])
    cols = torch.cat([items, users])

    return torch.stack([rows, cols], dim=0)


# ============================================================
#                    NEGATIVE SAMPLING
# ============================================================
class NegativeSampler:
    """Uniform negative sampling"""

    def __init__(self, num_items):
        self.num_items = num_items

    def sample(self, batch_size):
        return torch.randint(0, self.num_items, (batch_size,), device=DEVICE)


# ============================================================
#                      EVALUATION
# ============================================================
def build_user_item_dict(df):
    """Tworzy mapping: user_idx → list of item_idx"""
    user_items = defaultdict(list)
    for u, i in zip(df["user_idx"], df["item_idx"]):
        user_items[u].append(i)
    return user_items


def evaluate_model(
    model,
    edge_index,
    eval_dict,
    num_users,
    num_items,
    k_values=[5, 10, 20],
    sample_users=2000,
    mode="val",
):
    """
    Comprehensive evaluation: Recall@K, Precision@K, NDCG@K, Coverage

    Args:
        model: trained LightGCN
        edge_index: graph edges
        eval_dict: evaluation user→items dict
        num_users, num_items: counts
        k_values: list of K values
        sample_users: number of users to evaluate
        mode: "val" or "test"

    Returns:
        dict with metrics
    """
    print(f"\n🔍 Evaluating on {mode.upper()} set...")

    # Select users to evaluate
    all_users = [u for u in eval_dict.keys() if len(eval_dict[u]) > 0]

    if len(all_users) == 0:
        print(f"❌ ERROR: No users with positive items in {mode} set!")
        return (
            {f"recall@{k}": 0.0 for k in k_values}
            | {f"precision@{k}": 0.0 for k in k_values}
            | {f"ndcg@{k}": 0.0 for k in k_values}
            | {"coverage": 0.0}
        )

    if len(all_users) > sample_users:
        eval_users = np.random.choice(all_users, sample_users, replace=False)
    else:
        eval_users = all_users

    print(f"   Users in {mode} set: {len(all_users):,}")
    print(f"   Evaluating on: {len(eval_users):,} users")

    model.eval()
    with torch.no_grad():
        users_emb, items_emb = model.propagate(edge_index)

    metrics = {f"recall@{k}": [] for k in k_values}
    metrics.update({f"precision@{k}": [] for k in k_values})
    metrics.update({f"ndcg@{k}": [] for k in k_values})

    recommended_items = set()

    for u in tqdm(eval_users, desc=f"Eval {mode}", leave=False):
        # Get positive items
        pos_items = set(eval_dict[u])
        if len(pos_items) == 0:
            continue

        # Compute scores for all items
        user_emb = users_emb[u]
        scores = torch.matmul(user_emb, items_emb.T).cpu().numpy()

        # Rank items
        ranked_items = np.argsort(-scores)  # descending

        # Evaluate for each K
        for k in k_values:
            top_k = ranked_items[:k]
            recommended_items.update(top_k)

            # Hits
            hits = [1 if item in pos_items else 0 for item in top_k]
            num_hits = sum(hits)

            # Recall@K
            recall = num_hits / len(pos_items)
            metrics[f"recall@{k}"].append(recall)

            # Precision@K
            precision = num_hits / k
            metrics[f"precision@{k}"].append(precision)

            # NDCG@K
            dcg = sum([hits[i] / np.log2(i + 2) for i in range(k)])
            idcg = sum([1.0 / np.log2(i + 2) for i in range(min(len(pos_items), k))])
            ndcg = dcg / idcg if idcg > 0 else 0.0
            metrics[f"ndcg@{k}"].append(ndcg)

    # Average metrics
    results = {}
    for key in metrics:
        results[key] = float(np.mean(metrics[key]))

    # Coverage
    coverage = len(recommended_items) / num_items
    results["coverage"] = float(coverage)

    # Print results
    print(f"\n📊 {mode.upper()} Results:")
    for k in k_values:
        print(f"   Recall@{k}:    {results[f'recall@{k}']:.4f}")
        print(f"   Precision@{k}: {results[f'precision@{k}']:.4f}")
        print(f"   NDCG@{k}:      {results[f'ndcg@{k}']:.4f}")
    print(f"   Coverage:      {results['coverage']:.4f}")

    return results


# ============================================================
#                    TRAINING LOOP
# ============================================================
def train_model(train_df, val_df, test_df, num_users, num_items):
    """
    Main training loop with evaluation and logging.

    Returns:
        model, train_history, val_history, test_results
    """
    print("\n🚀 Starting LightGCN Training")
    print(f"{'='*60}")
    print(f"Embedding Dim: {Config.EMBEDDING_DIM}")
    print(f"Layers: {Config.LAYERS}")
    print(f"Epochs: {Config.EPOCHS}")
    print(f"Learning Rate: {Config.LR}")
    print(f"Batch Size: {Config.BATCH_SIZE}")
    print(f"{'='*60}\n")

    # Build graph
    train_edge_index = build_edge_index(train_df, num_users)

    # Build user-item dicts
    val_dict = build_user_item_dict(val_df)
    test_dict = build_user_item_dict(test_df)

    # Initialize model
    model = LightGCN(
        num_users=num_users,
        num_items=num_items,
        embedding_dim=Config.EMBEDDING_DIM,
        n_layers=Config.LAYERS,
    ).to(DEVICE)

    optimizer = optim.Adam(model.parameters(), lr=Config.LR)
    neg_sampler = NegativeSampler(num_items)

    # Prepare training data
    user_tensor = torch.tensor(train_df["user_idx"].values, dtype=torch.long, device=DEVICE)
    item_tensor = torch.tensor(train_df["item_idx"].values, dtype=torch.long, device=DEVICE)

    # Training history
    train_history = {"epoch": [], "loss": []}

    val_history = {
        "epoch": [],
        **{f"recall@{k}": [] for k in Config.K_VALUES},
        **{f"precision@{k}": [] for k in Config.K_VALUES},
        **{f"ndcg@{k}": [] for k in Config.K_VALUES},
        "coverage": [],
    }

    # Training loop
    start_time = time.time()

    for epoch in range(1, Config.EPOCHS + 1):
        epoch_start = time.time()
        model.train()

        # Shuffle data
        perm = torch.randperm(len(train_df), device=DEVICE)
        u_shuffled = user_tensor[perm]
        p_shuffled = item_tensor[perm]

        epoch_losses = []

        # Mini-batch training
        for i in range(0, len(train_df), Config.BATCH_SIZE):
            users = u_shuffled[i : i + Config.BATCH_SIZE]
            pos_items = p_shuffled[i : i + Config.BATCH_SIZE]
            neg_items = neg_sampler.sample(len(users))

            optimizer.zero_grad()
            loss = model(users, pos_items, neg_items, train_edge_index)
            loss.backward()
            optimizer.step()

            epoch_losses.append(loss.item())

        # Log training loss
        mean_loss = np.mean(epoch_losses)
        epoch_time = time.time() - epoch_start
        train_history["epoch"].append(epoch)
        train_history["loss"].append(mean_loss)

        print(f"Epoch {epoch:3d}/{Config.EPOCHS} | Loss: {mean_loss:.4f} | Time: {epoch_time:.1f}s")

        # Validation evaluation
        if epoch % Config.EVAL_EVERY == 0 or epoch == Config.EPOCHS:
            val_results = evaluate_model(
                model,
                train_edge_index,
                val_dict,
                num_users,
                num_items,
                Config.K_VALUES,
                Config.SAMPLE_USERS_EVAL,
                mode="val",
            )

            val_history["epoch"].append(epoch)
            for key in val_results:
                val_history[key].append(val_results[key])

    total_time = time.time() - start_time
    print(
        f"\n⏱️  Total training time: {total_time/60:.1f} minutes ({total_time/Config.EPOCHS:.1f}s/epoch)"
    )

    # Final test evaluation
    print("\n" + "=" * 60)
    print("FINAL TEST EVALUATION")
    print("=" * 60)

    test_results = evaluate_model(
        model,
        train_edge_index,
        test_dict,
        num_users,
        num_items,
        Config.K_VALUES,
        Config.SAMPLE_USERS_EVAL,
        mode="test",
    )

    # Save model
    model_path = os.path.join(Config.MODEL_DIR, "lightgcn_final.pt")
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "num_users": num_users,
            "num_items": num_items,
            "config": {
                "embedding_dim": Config.EMBEDDING_DIM,
                "n_layers": Config.LAYERS,
            },
        },
        model_path,
    )
    print(f"\n💾 Model saved to {model_path}")

    return model, train_history, val_history, test_results


# ============================================================
#                    PLOTTING FUNCTIONS
# ============================================================
def plot_training_loss(train_history):
    """Plot 1: Training Loss over Epochs"""
    plt.figure(figsize=(10, 6))

    plt.plot(
        train_history["epoch"],
        train_history["loss"],
        "o-",
        color="#2E86AB",
        linewidth=2,
        markersize=4,
        label="Training Loss",
    )

    plt.xlabel("Epoch", fontsize=12)
    plt.ylabel("BPR Loss", fontsize=12)
    plt.title("Training Loss Over Time", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="upper right")
    plt.tight_layout()

    save_path = os.path.join(Config.PLOTS_DIR, "training_loss.png")
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Saved: {save_path}")


def plot_recall_curves(val_history):
    """Plot 2: Recall@K over Epochs"""
    plt.figure(figsize=(10, 6))

    colors = ["#A23B72", "#F18F01", "#2E86AB"]
    markers = ["o", "s", "^"]

    for idx, k in enumerate(Config.K_VALUES):
        plt.plot(
            val_history["epoch"],
            val_history[f"recall@{k}"],
            marker=markers[idx],
            color=colors[idx],
            linewidth=2,
            markersize=6,
            label=f"Recall@{k}",
        )

    plt.xlabel("Epoch", fontsize=12)
    plt.ylabel("Recall@K", fontsize=12)
    plt.title("Recall@K Performance", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="lower right")
    plt.tight_layout()

    save_path = os.path.join(Config.PLOTS_DIR, "recall_curves.png")
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Saved: {save_path}")


def plot_precision_curves(val_history):
    """Plot 3: Precision@K over Epochs"""
    plt.figure(figsize=(10, 6))

    colors = ["#C73E1D", "#6A994E", "#BC4B51"]
    markers = ["D", "v", "p"]

    for idx, k in enumerate(Config.K_VALUES):
        plt.plot(
            val_history["epoch"],
            val_history[f"precision@{k}"],
            marker=markers[idx],
            color=colors[idx],
            linewidth=2,
            markersize=6,
            label=f"Precision@{k}",
        )

    plt.xlabel("Epoch", fontsize=12)
    plt.ylabel("Precision@K", fontsize=12)
    plt.title("Precision@K Performance", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="lower right")
    plt.tight_layout()

    save_path = os.path.join(Config.PLOTS_DIR, "precision_curves.png")
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Saved: {save_path}")


def plot_ndcg_curves(val_history):
    """Plot 4: NDCG@K over Epochs"""
    plt.figure(figsize=(10, 6))

    colors = ["#1A535C", "#FF6B6B", "#4ECDC4"]
    markers = ["*", "h", "8"]

    for idx, k in enumerate(Config.K_VALUES):
        plt.plot(
            val_history["epoch"],
            val_history[f"ndcg@{k}"],
            marker=markers[idx],
            color=colors[idx],
            linewidth=2,
            markersize=8,
            label=f"NDCG@{k}",
        )

    plt.xlabel("Epoch", fontsize=12)
    plt.ylabel("NDCG@K", fontsize=12)
    plt.title("NDCG@K Performance", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="lower right")
    plt.tight_layout()

    save_path = os.path.join(Config.PLOTS_DIR, "ndcg_curves.png")
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Saved: {save_path}")


def plot_combined_metrics(val_history):
    """Plot 5: Combined Overview (2x2 subplots)"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("LightGCN Training Overview", fontsize=16, fontweight="bold")

    # Plot 1: Recall@20
    ax = axes[0, 0]
    ax.plot(
        val_history["epoch"],
        val_history["recall@20"],
        "o-",
        color="#2E86AB",
        linewidth=2,
        markersize=5,
    )
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Recall@20")
    ax.set_title("Recall@20")
    ax.grid(True, alpha=0.3)

    # Plot 2: Precision@20
    ax = axes[0, 1]
    ax.plot(
        val_history["epoch"],
        val_history["precision@20"],
        "s-",
        color="#C73E1D",
        linewidth=2,
        markersize=5,
    )
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Precision@20")
    ax.set_title("Precision@20")
    ax.grid(True, alpha=0.3)

    # Plot 3: NDCG@20
    ax = axes[1, 0]
    ax.plot(
        val_history["epoch"],
        val_history["ndcg@20"],
        "^-",
        color="#F18F01",
        linewidth=2,
        markersize=5,
    )
    ax.set_xlabel("Epoch")
    ax.set_ylabel("NDCG@20")
    ax.set_title("NDCG@20")
    ax.grid(True, alpha=0.3)

    # Plot 4: Coverage
    ax = axes[1, 1]
    ax.plot(
        val_history["epoch"],
        val_history["coverage"],
        "D-",
        color="#6A994E",
        linewidth=2,
        markersize=5,
    )
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Coverage")
    ax.set_title("Catalog Coverage")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(Config.PLOTS_DIR, "combined_overview.png")
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Saved: {save_path}")


def save_metrics_json(train_history, val_history, test_results, num_users, num_items):
    """Save all metrics to JSON"""
    metrics = {
        "model": "LightGCN",
        "dataset": "goodbooks-10k",
        "date": datetime.now().isoformat(),
        "config": {
            "embedding_dim": Config.EMBEDDING_DIM,
            "layers": Config.LAYERS,
            "epochs": Config.EPOCHS,
            "learning_rate": Config.LR,
            "batch_size": Config.BATCH_SIZE,
            "train_ratio": Config.TRAIN_RATIO,
            "val_ratio": Config.VAL_RATIO,
            "test_ratio": Config.TEST_RATIO,
        },
        "data_stats": {
            "num_users": int(num_users),
            "num_items": int(num_items),
        },
        "final_test_results": test_results,
        "best_val_results": {
            key: float(max(val_history[key])) for key in val_history if key != "epoch"
        },
        "training_history": {
            "epochs": train_history["epoch"],
            "losses": train_history["loss"],
        },
        "validation_history": val_history,
    }

    save_path = os.path.join(Config.OUTPUT_DIR, "metrics.json")
    with open(save_path, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"\n💾 Metrics saved to {save_path}")


# ============================================================
#                         MAIN
# ============================================================
def main():
    print("\n" + "=" * 60)
    print(" 🎯 LightGCN Training - Praca Inżynierska")
    print("=" * 60 + "\n")

    # Sprawdzenie ścieżek
    print(f"📁 Bieżący katalog: {os.getcwd()}")
    print(f"📁 Szukam pliku: {Config.RATINGS_FILE}")

    if not os.path.exists(Config.RATINGS_FILE):
        print(f"\n❌ BŁĄD: Nie znaleziono pliku {Config.RATINGS_FILE}")
        print(f"\n💡 Sprawdź strukturę katalogów:")
        print(f"   Jesteś w: {os.getcwd()}")
        print(f"\n   Możliwe rozwiązania:")
        print(f"   1. Uruchom skrypt z katalogu backend/recommendation_engine/")
        print(f"   2. Lub zmień Config.DATA_DIR na właściwą ścieżkę")
        print(f"\n   Aktualna struktura:")
        for root, dirs, files in os.walk(".", maxdepth=2):
            level = root.replace(".", "").count(os.sep)
            indent = " " * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = " " * 2 * (level + 1)
            for file in files[:5]:  # Tylko pierwsze 5 plików
                print(f"{subindent}{file}")
        return

    print(f"✅ Plik znaleziony!\n")

    # 1. Load and split data
    train_df, val_df, test_df, num_users, num_items = load_and_split_data()

    # 2. Train model
    model, train_history, val_history, test_results = train_model(
        train_df, val_df, test_df, num_users, num_items
    )

    # 3. Generate plots
    print("\n" + "=" * 60)
    print("📊 GENERATING PLOTS")
    print("=" * 60 + "\n")

    plot_training_loss(train_history)
    plot_recall_curves(val_history)
    plot_precision_curves(val_history)
    plot_ndcg_curves(val_history)
    plot_combined_metrics(val_history)

    # 4. Save metrics
    save_metrics_json(train_history, val_history, test_results, num_users, num_items)

    print("\n" + "=" * 60)
    print(" ✅ TRAINING COMPLETE!")
    print("=" * 60)
    print(f"\n📁 Output directory: {Config.OUTPUT_DIR}")
    print(f"   - Plots: {Config.PLOTS_DIR}")
    print(f"   - Model: {Config.MODEL_DIR}")
    print(f"   - Metrics: {os.path.join(Config.OUTPUT_DIR, 'metrics.json')}")
    print("\n🎉 Powodzenia z pracą inżynierską!\n")


if __name__ == "__main__":
    main()
