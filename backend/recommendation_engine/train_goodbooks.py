import torch
import numpy as np
from torch import optim
import scipy.sparse as sp

# === KONFIGURACJA ===
EMBEDDING_DIM = 64
N_LAYERS = 3
LEARNING_RATE = 0.001
BATCH_SIZE = 2048
EPOCHS = 1000
REG_WEIGHT = 1e-4
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

print(f"Device: {DEVICE}")

# === ŁADOWANIE DANYCH ===
def load_data(path):
    user_items = {}
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            user = int(parts[0])
            items = [int(x) for x in parts[1:]]
            user_items[user] = items
    return user_items

train_data = load_data('data/processed/train.txt')
test_data = load_data('data/processed/test.txt')

n_users = max(train_data.keys()) + 1
n_items = max(max(items) for items in train_data.values()) + 1

print(f"Users: {n_users}, Items: {n_items}")

# === BUDOWA GRAFU ===
row, col = [], []
for user, items in train_data.items():
    for item in items:
        row.append(user)
        col.append(item)

R = sp.csr_matrix((np.ones(len(row)), (row, col)), shape=(n_users, n_items))

# Macierz sąsiedztwa: [[0, R], [R^T, 0]]
adj = sp.bmat([[None, R], [R.T, None]]).tocsr()

# Normalizacja: D^(-1/2) * A * D^(-1/2)
degrees = np.array(adj.sum(1)).flatten()
d_inv_sqrt = np.power(degrees, -0.5)
d_inv_sqrt[np.isinf(d_inv_sqrt)] = 0.
D = sp.diags(d_inv_sqrt)
norm_adj = D @ adj @ D

# Do PyTorch
coo = norm_adj.tocoo()
indices = torch.LongTensor([coo.row, coo.col])
values = torch.FloatTensor(coo.data)
norm_adj_tensor = torch.sparse_coo_tensor(indices, values, coo.shape).to(DEVICE)

# === MODEL ===
class LightGCN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.user_emb = torch.nn.Embedding(n_users, EMBEDDING_DIM)
        self.item_emb = torch.nn.Embedding(n_items, EMBEDDING_DIM)
        torch.nn.init.xavier_uniform_(self.user_emb.weight)
        torch.nn.init.xavier_uniform_(self.item_emb.weight)
    
    def forward(self):
        all_emb = torch.cat([self.user_emb.weight, self.item_emb.weight])
        embs = [all_emb]
        for _ in range(N_LAYERS):
            all_emb = torch.sparse.mm(norm_adj_tensor, all_emb)
            embs.append(all_emb)
        all_emb = torch.mean(torch.stack(embs), dim=0)
        return all_emb[:n_users], all_emb[n_users:]

model = LightGCN().to(DEVICE)
optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

# === TRENING ===
# Przygotuj dane treningowe
train_users, train_items = [], []
for user, items in train_data.items():
    for item in items:
        train_users.append(user)
        train_items.append(item)

train_users = np.array(train_users)
train_items = np.array(train_items)

print(f"Training pairs: {len(train_users):,}")

best_recall = 0
for epoch in range(EPOCHS):
    model.train()
    
    # Shuffle
    perm = np.random.permutation(len(train_users))
    
    total_loss = 0
    n_batches = (len(train_users) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_idx in range(n_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(train_users))
        
        batch_users = torch.LongTensor(train_users[perm[start:end]]).to(DEVICE)
        batch_pos = torch.LongTensor(train_items[perm[start:end]]).to(DEVICE)
        
        # Negative sampling
        batch_neg = torch.LongTensor(np.random.randint(0, n_items, end-start)).to(DEVICE)
        
        optimizer.zero_grad()
        user_emb, item_emb = model()
        
        u = user_emb[batch_users]
        pos = item_emb[batch_pos]
        neg = item_emb[batch_neg]
        
        pos_scores = (u * pos).sum(dim=1)
        neg_scores = (u * neg).sum(dim=1)
        
        # BPR Loss
        loss = -torch.log(torch.sigmoid(pos_scores - neg_scores) + 1e-10).mean()
        
        # Regularization
        reg = (model.user_emb(batch_users).norm(2).pow(2) + 
               model.item_emb(batch_pos).norm(2).pow(2) +
               model.item_emb(batch_neg).norm(2).pow(2)) / (2 * len(batch_users))
        
        loss = loss + REG_WEIGHT * reg
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    # Ewaluacja co 10 epok
    if (epoch + 1) % 10 == 0:
        model.eval()
        with torch.no_grad():
            user_emb, item_emb = model()
            
            # Recall@20
            recalls = []
            for user_id, test_items in test_data.items():
                if user_id not in train_data:
                    continue
                
                scores = (user_emb[user_id] @ item_emb.T).cpu().numpy()
                
                # Maskuj train items
                for item in train_data[user_id]:
                    scores[item] = -np.inf
                
                top20 = np.argsort(scores)[-20:]
                hits = len(set(top20) & set(test_items))
                recalls.append(hits / len(test_items))
            
            recall = np.mean(recalls)
            
            print(f"Epoch {epoch+1}: Loss={total_loss/n_batches:.4f}, Recall@20={recall:.4f}")
            
            if recall > best_recall:
                best_recall = recall
                torch.save({
                    'model': model.state_dict(),
                    'user_emb': user_emb.cpu(),
                    'item_emb': item_emb.cpu(),
                }, 'trained_models/goodbooks_lightgcn_best.pt')
                print(f"  ✅ Saved best model!")

print(f"\nBest Recall@20: {best_recall:.4f}")