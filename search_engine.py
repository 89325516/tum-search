import json
import torch
import numpy as np
import random
import sys
import os
from dotenv import load_dotenv

load_dotenv()
from qdrant_client import QdrantClient

# Add root to path
sys.path.append(os.getcwd())
from consistency_engine import ConsistencyEngine

from transformers import CLIPProcessor, CLIPModel
from scipy.stats import rankdata

# ================= 配置区 =================
# 🔴 你的真实配置
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
SPACE_X = "tum_space_x"
# =========================================

print("🛠️Initializing Search Engine...")

# 1. 连接 Qdrant
print("🔗Connecting to Qdrant Database...")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# 2. 加载本地 CLIP (CPU模式)
print("⚙️Loading local CLIP model (CPU mode)...")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# 3. 初始化一致性引擎
consistency_engine = ConsistencyEngine()

# --- 辅助函数：高斯秩归一化 ---
def gauss_rank_norm(scores):
    if not scores: return []
    ranks = rankdata(scores, method='average')
    return (ranks / len(scores)).tolist()

# --- 核心搜索函数 ---
def search(query_text, top_k=10):
    print(f"\n🔍 Searching for: '{query_text}' ...")

    # ---------------------------------------------------------
    # Layer 1: Vector Embedding (CLIP)
    # ---------------------------------------------------------
    inputs = clip_processor(text=[query_text], return_tensors="pt", padding=True)
    with torch.no_grad():
        query_vector = clip_model.get_text_features(**inputs)
        query_vector = query_vector / query_vector.norm(p=2, dim=-1, keepdim=True)
        query_vector = query_vector[0].numpy().tolist()

    # ---------------------------------------------------------
    # Layer 2: Qdrant Search (HNSW)
    # ---------------------------------------------------------
    # 直接查询 Space X (包含所有内容)
    try:
        hits = client.query_points(
            collection_name=SPACE_X,
            query=query_vector,
            using="clip",
            limit=top_k * 3  # 多取一些用于重排
        ).points
    except Exception as e:
        print(f"❌ Qdrant search failed: {e}")
        return []

    # ---------------------------------------------------------
    # Layer 3: Fusion & Ranking & Safeguards
    # ---------------------------------------------------------
    results = []
    raw_sims = []
    raw_prs = []
    
    total_candidates = len(hits)

    for rank_idx, hit in enumerate(hits):
        hit_id = hit.id
        sim = hit.score
        payload = hit.payload

        # 获取权威度 (PageRank)
        pr = payload.get('pr_score', 0.0)

        # --- 第四道防线：一致性校验 (Consistency Check) ---
        # 检查 CLIP 排名与 DINO 排名的冲突 (Mock)
        is_consistent, conflict_loss = consistency_engine.check_consistency(
            query_text, payload, rank_idx, total_candidates
        )
        
        if not is_consistent:
            print(f"🛡️ [Circuit Breaker] Blocked ID {hit_id}: High Semantic-Visual Conflict (Loss: {conflict_loss:.2f})")
            continue

        raw_sims.append(sim)
        raw_prs.append(pr)

        results.append({
            "id": hit_id,
            "sim": sim,
            "pr": pr,
            "payload": payload,
            "conflict_loss": conflict_loss
        })

    # 4. 归一化处理 (Gauss Rank)
    norm_sims = gauss_rank_norm(raw_sims)
    norm_prs = gauss_rank_norm(raw_prs)

    final_ranked = []

    # 权重设定
    w_sim = 0.7
    w_pr = 0.3

    for i, item in enumerate(results):
        # 最终打分公式
        final_score = w_sim * norm_sims[i] + w_pr * norm_prs[i]

        # 解析内容
        p = item['payload']
        content_type = p.get('type', 'unknown')
        url = p.get('url', '#')
        preview = p.get('content_preview', 'No preview')
        if isinstance(preview, list): preview = preview[0]

        final_ranked.append({
            "score": final_score,
            "type": content_type,
            "url": url,
            "content": preview,
            "id": item['id'],
            "is_exploration": False
        })

    # 5. 排序
    final_ranked.sort(key=lambda x: x['score'], reverse=True)
    
    # --- 第三道防线 (B)：探索红利 (Exploration Bonus) ---
    # 随机插入新内容 (Bandit 算法)
    if random.random() < 0.05: # 5% 概率触发
        print("🎲 [Exploration] Triggering exploration mechanism, injecting new content...")
        # 这里简单模拟：随机取一个低分结果提升到第 2 名
        if len(final_ranked) > 5:
            lucky_idx = random.randint(5, len(final_ranked)-1)
            lucky_item = final_ranked.pop(lucky_idx)
            lucky_item['is_exploration'] = True
            lucky_item['score'] += 0.5 # 强行加分
            final_ranked.insert(1, lucky_item) # 插入到第二位

    return final_ranked[:top_k]


# --- 结果展示 ---
def display_results(results):
    print("\n" + "=" * 40)
    print("      SEARCH RESULTS (Top 5)      ")
    print("=" * 40)

    if not results:
        print("No results found.")
        return

    for i, res in enumerate(results[:5]):
        icon = "📄"
        if res['type'] == 'image':
            icon = "🖼️"
        elif res['type'] == 'audio':
            icon = "🎵"
            
        explore_tag = " [🎲 EXPLORE]" if res.get('is_exploration') else ""

        print(f"{i + 1}. {icon} [{res['type'].upper()}]{explore_tag} (Score: {res['score']:.4f})")
        print(f"   🔗 URL: {res['url']}")
        content_str = str(res['content'])
        print(f"   📝 Content: {content_str[:100]}...")
        print("-" * 40)


# --- 主程序入口 ---
if __name__ == "__main__":
    while True:
        q = input("\n请输入搜索关键词 (输入 'exit' 退出): ")
        if q.lower() == 'exit': break

        results = search(q)
        display_results(results)