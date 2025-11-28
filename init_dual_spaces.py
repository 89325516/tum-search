from qdrant_client import QdrantClient
from qdrant_client.http import models

# ================= 配置 =================
import os
from dotenv import load_dotenv

load_dotenv()

# 修改前：
# QDRANT_URL = "https://..."
# QDRANT_API_KEY = "ey..."

# 修改后：
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def create_collection_if_not_exists(name, vector_size=512):
    # 如果存在先删除 (保证干净的实验环境)
    try:
        client.delete_collection(name)
        print(f"🗑️ 已清空旧集合: {name}")
    except:
        pass

    # 创建新集合
    client.create_collection(
        collection_name=name,
        vectors_config={
            "clip": models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
        }
    )
    print(f"✅ 已创建集合: {name}")


if __name__ == "__main__":
    print("正在初始化双空间架构...")
    # 1. 创建 Space R (Reference) - 也就是元老院
    create_collection_if_not_exists("tum_space_r")

    # 2. 创建 Space X (Main Storage) - 也就是搜索池
    create_collection_if_not_exists("tum_space_x")

    print("\n双空间初始化完成！等待数据注入。")