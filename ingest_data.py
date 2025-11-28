import pickle
import torch
import numpy as np
import requests
import uuid
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

# ================= 配置区 =================
import os

# 修改前：
# QDRANT_URL = "https://..."
# QDRANT_API_KEY = "ey..."

# 修改后：
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION_NAME = "tum_data"
# =========================================

# 1. 加载资源 (模型 + 锚点)
print("⚙️Initializing Ingestion Pipeline...")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# 加载“元老院”数据
try:
    with open('mock_data/anchors.pkl', 'rb') as f:
        ANCHORS = pickle.load(f)
    print(f"Loaded {len(ANCHORS)} anchor data points.")
except FileNotFoundError:
    print("❌ Error: anchors.pkl not found. Please run Step 1 script first.")
    exit()


# --- 核心算法：基于投影的实时打分 ---
def calculate_projected_score(target_vector):
    """
    计算公式: Score(x) = Sum( Sim(x, anchor_i) * PR(anchor_i) )
    """
    scores = []
    # 1. 计算与所有锚点的相似度
    for anchor in ANCHORS:
        # Cosine Similarity
        sim = np.dot(target_vector, anchor['vector'])
        if sim > 0:  # 只考虑正相关
            scores.append({
                "sim": sim,
                "anchor_pr": anchor['pr_score']
            })

    # 2. 排序，取 Top 5 相似的锚点
    scores.sort(key=lambda x: x['sim'], reverse=True)
    top_k = scores[:5]

    # 3. 加权求和
    final_score = 0.0
    for item in top_k:
        final_score += item['sim'] * item['anchor_pr']

    # 转换为 Python float
    return float(final_score)


# --- 向量化工具 ---
def get_clip_embedding(text=None, image_path=None):
    inputs = None
    if text:
        # 加入 truncation 防止过长报错
        inputs = clip_processor(
            text=[text],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=77
        )
        feat = clip_model.get_text_features(**inputs)
    elif image_path:
        try:
            image = Image.open(image_path).convert("RGB")
            inputs = clip_processor(images=image, return_tensors="pt")
            feat = clip_model.get_image_features(**inputs)
        except Exception as e:
            print(f"❌🌌Image read failed: {e}")
            return None

    if inputs is not None:
        feat = feat / feat.norm(p=2, dim=-1, keepdim=True)
        return feat[0].detach().numpy()
    return None


# --- 上传工具 (REST API) ---
def upload_to_qdrant(points):
    base_url = QDRANT_URL.rstrip('/')
    url = f"{base_url}/collections/{COLLECTION_NAME}/points?wait=true"

    headers = {
        "api-key": QDRANT_API_KEY,
        "Content-Type": "application/json"
    }

    # 构造 payload
    batch_points = []
    for p in points:
        # ⚠️ 关键修正：对于 named vectors，直接使用 { "name": [vector] } 的字典格式
        # 不需要嵌套 "name": "clip", "vector": ...

        vector_struct = {}
        if p['vector_name'] == 'clip':
            vector_struct['clip'] = p['vector'].tolist()
            # 如果之前定义了 'dino' 且是必须的，可以在这里补零，但通常 sparse 也是允许的
            # 为了兼容性，我们只传 clip

        batch_points.append({
            "id": str(uuid.uuid4()),
            "vector": vector_struct,  # <--- 修正后的结构
            "payload": p['payload']
        })

    try:
        resp = requests.put(url, headers=headers, json={"points": batch_points})

        if resp.status_code != 200:
            print(f"❌ Server returned error: {resp.status_code}")
            print(resp.text)
        else:
            print(f"✅ Successfully ingested {len(points)} items! (With real-time scoring)")

    except Exception as e:
        print(f"❌ Ingestion request failed: {e}")


# --- 主入口函数：添加新内容 ---
def add_new_content(url, text_content=None, image_path=None):
    points_to_upload = []

    # 1. 处理文本部分
    if text_content:
        print(f"⚙️Processing text: {text_content[:30]}...")
        vec = get_clip_embedding(text=text_content)
        if vec is not None:
            pr_score = calculate_projected_score(vec)

            points_to_upload.append({
                "vector": vec,
                "vector_name": "clip",  # 标记这是 CLIP 向量
                "payload": {
                    "url": url,
                    "type": "text",
                    "content_preview": text_content[:100],
                    "pr_score": pr_score,
                    "is_new": True
                }
            })
            print(f"   -> ✅Text score: {pr_score:.6f}")

    # 2. 处理图像部分
    if image_path:
        print(f"⚙️Processing image: {image_path}...")
        vec = get_clip_embedding(image_path=image_path)
        if vec is not None:
            pr_score = calculate_projected_score(vec)
            # 注意：图片这里我们也暂时作为 CLIP 向量上传，因为我们的搜索主要基于语义
            # 如果你有专门的 DINO 搜索需求，需要在这里区分
            points_to_upload.append({
                "vector": vec,
                "vector_name": "clip",
                "payload": {
                    "url": url,
                    "type": "image",
                    "content_preview": "Image content",
                    "pr_score": pr_score,
                    "is_new": True
                }
            })
            print(f"   -> ✅🌌Image score: {pr_score:.6f}")

    # 3. 执行上传
    if points_to_upload:
        upload_to_qdrant(points_to_upload)


# --- 测试用例 ---
if __name__ == "__main__":
    print("-" * 50)
    print("⚙️Simulating new data entering the system...")

    new_url = "https://google.com/search/pagerank_explained"
    new_text = "PageRank works by counting the number and quality of links to a page to determine a rough estimate of how important the website is."

    # 运行
    add_new_content(new_url, text_content=new_text)