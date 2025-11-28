import json
import torch
import pickle
import numpy as np
from transformers import CLIPProcessor, CLIPModel

# ================= 配置 =================
# 我们只选最权威的 50 个节点作为锚点
TOP_K_ANCHORS = 50
# =======================================

print("正在构建'元老院' (Anchors Cache)...")

# 1. 加载之前的计算结果
try:
    with open('mock_data/pagerank_scores.json', 'r') as f:
        scores = json.load(f)
    with open('mock_data/tum_content.json', 'r') as f:
        content_list = json.load(f)
except FileNotFoundError:
    print("❌ 错误：找不到数据文件。请确保 mock_data 文件夹下有 pagerank_scores.json 和 tum_content.json")
    exit()

# 将内容转为字典方便查找
content_dict = {item['id']: item for item in content_list}

# 2. 选出分数最高的 Top K
# 注意：确保 key 转为 int 且在 content_dict 中存在
sorted_ids = sorted([int(k) for k in scores.keys()], key=lambda k: scores[str(k)], reverse=True)
valid_anchors_ids = [aid for aid in sorted_ids if aid in content_dict][:TOP_K_ANCHORS]

# 3. 加载 CLIP 模型 (CPU模式)
print("正在加载 CLIP 模型...")
device = "cpu"
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

anchors = []

print(f"正在计算 {len(valid_anchors_ids)} 个锚点的向量指纹...")

for aid in valid_anchors_ids:
    item = content_dict.get(aid)
    if not item: continue

    # 提取锚点的核心特征
    # 如果内容是纯文本，直接用；如果是图片，这里暂时用图片的文字描述来代替锚点特征
    # (因为锚点库需要统一的向量空间，用 Text Encoder 生成锚点是最稳健的基准)
    text_content = item.get('content', item.get('content_desc', ''))

    # ⚠️ 修正点：加入 truncation=True 和 max_length=77
    inputs = processor(
        text=[text_content],
        return_tensors="pt",
        padding=True,
        truncation=True,  # <--- 关键修复：强制截断过长的文本
        max_length=77  # <--- 关键修复：限制最大长度为 CLIP 的上限
    )

    with torch.no_grad():
        emb = model.get_text_features(**inputs)
        emb = emb / emb.norm(p=2, dim=-1, keepdim=True)  # 归一化

    anchors.append({
        "id": aid,
        "pr_score": scores[str(aid)],  # 它的权威分 (家产)
        "vector": emb[0].numpy()  # 它的长相 (用于对比)
    })

# 4. 保存锚点数据到本地
if anchors:
    with open('mock_data/anchors.pkl', 'wb') as f:
        pickle.dump(anchors, f)
    print(f"✅ '元老院'构建完成！已保存 {len(anchors)} 个锚点至 mock_data/anchors.pkl")
    print("💡 下一步：请运行 Step 2 (ingest_data.py) 来测试新数据入库和实时打分。")
else:
    print("❌ 警告：生成的锚点列表为空，请检查 pagerank_scores.json 是否有数据。")