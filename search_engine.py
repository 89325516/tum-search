import json
import torch
import numpy as np
import random
import sys
import os
import re
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

# --- 辅助函数：生成高亮摘要 ---
def generate_highlighted_snippet(text: str, query: str, snippet_length: int = 200) -> str:
    """
    从文本中提取包含关键词的摘要片段，并用特殊标记包裹关键词以便前端高亮
    
    Args:
        text: 原始文本
        query: 搜索查询（可能包含多个关键词）
        snippet_length: 摘要片段的最大长度
        
    Returns:
        包含高亮标记的摘要片段，格式：...前文 [[HIGHLIGHT]]关键词[[/HIGHLIGHT]] 后文...
    """
    if not text or not query:
        return text[:snippet_length] if text else ""
    
    text_lower = text.lower()
    query_lower = query.lower()
    
    # 提取查询中的关键词（去除常见停用词）
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
    keywords = [word.strip() for word in re.split(r'[\s,\.;:]+', query_lower) 
                if word.strip() and word.strip() not in stop_words and len(word.strip()) > 2]
    
    if not keywords:
        keywords = [query_lower]
    
    # 查找所有关键词在文本中的位置
    positions = []
    for keyword in keywords:
        # 使用正则表达式进行不区分大小写的搜索
        pattern = re.escape(keyword)
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            positions.append((match.start(), match.end(), keyword))
    
    # 按位置排序
    positions.sort(key=lambda x: x[0])
    
    if not positions:
        # 如果没找到关键词，返回文本开头
        return text[:snippet_length]
    
    # 选择第一个匹配位置作为中心（或选择包含最多关键词的区域）
    center_start, center_end, matched_keyword = positions[0]
    
    # 尝试找到一个包含更多关键词的窗口
    # 计算一个可以包含多个关键词的窗口大小
    best_start = center_start
    best_end = min(len(text), center_start + snippet_length)
    
    # 尝试向后扩展，看看能否包含更多关键词
    for pos_start, pos_end, _ in positions[1:]:
        if pos_end <= center_start + snippet_length:
            best_end = pos_end + snippet_length // 4  # 扩展一点以包含后面的关键词
    
    # 计算摘要的起始位置（向前扩展）
    snippet_start = max(0, best_start - snippet_length // 2)
    
    # 计算摘要的结束位置（向后扩展）
    snippet_end = min(len(text), best_end + snippet_length // 4)
    
    # 如果摘要从文本中间开始，添加省略号
    prefix = "..." if snippet_start > 0 else ""
    
    # 如果摘要未到达文本末尾，添加省略号
    suffix = "..." if snippet_end < len(text) else ""
    
    # 提取摘要片段
    snippet = text[snippet_start:snippet_end]
    
    # 在摘要中高亮所有关键词
    highlighted_snippet = snippet
    for keyword in keywords:
        # 使用正则表达式匹配关键词（不区分大小写）
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        highlighted_snippet = pattern.sub(
            lambda m: f"[[HIGHLIGHT]]{m.group()}[[/HIGHLIGHT]]",
            highlighted_snippet
        )
    
    return prefix + highlighted_snippet + suffix

def extract_keywords_from_query(query: str) -> list:
    """
    从查询中提取关键词
    """
    # 去除标点符号和常见停用词
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'what', 'where', 'when', 'why', 'how'}
    keywords = [word.strip() for word in re.split(r'[\s,\.;:]+', query.lower()) 
                if word.strip() and word.strip() not in stop_words and len(word.strip()) > 2]
    return keywords if keywords else [query.lower()]

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
        
        # 获取完整文本用于生成高亮摘要（优先使用full_text，否则使用content或content_preview）
        full_text = p.get('full_text', '') or p.get('content', '') or preview
        
        # 生成高亮摘要
        highlighted_snippet = generate_highlighted_snippet(
            full_text if isinstance(full_text, str) else str(full_text), 
            query_text, 
            snippet_length=200
        )

        final_ranked.append({
            "score": final_score,
            "type": content_type,
            "url": url,
            "content": preview,
            "highlighted_snippet": highlighted_snippet,  # 新增：包含高亮标记的摘要
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