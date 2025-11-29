import numpy as np
import uuid
import time
import random
import logging
from typing import Optional, Dict, List
from qdrant_client import QdrantClient
from qdrant_client.http import models
import google.generativeai as genai
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from crawler import SmartCrawler  # 确保 crawler.py 在同级目录下

logger = logging.getLogger(__name__)

# ================= 配置区 =================
# 🔴 你的真实配置
import os
from dotenv import load_dotenv

load_dotenv()

# 修改前：
# QDRANT_URL = "https://..."
# QDRANT_API_KEY = "ey..."

# 修改后：
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    print("⚠️ GOOGLE_API_KEY not found in .env. Summarization will be disabled.")

SPACE_R = "tum_space_r"
SPACE_X = "tum_space_x"

# 阈值设定
NOVELTY_THRESHOLD = 0.2  # 距离大于 0.2 (相似度 < 0.8) 视为独特，自动晋升
# =========================================

print("🛠️System Initialization: Connecting to database & loading models...")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
crawler = SmartCrawler()
from interaction_manager import InteractionManager

def get_embedding(text=None, image_path=None):
    inputs = None
    if text:
        inputs = clip_processor(text=[text], return_tensors="pt", padding=True, truncation=True, max_length=77)
        feat = clip_model.get_text_features(**inputs)
    elif image_path:
        try:
            # 如果是URL图片，需要先下载，这里简化为兼容本地路径
            image = Image.open(image_path).convert("RGB")
            inputs = clip_processor(images=image, return_tensors="pt")
            feat = clip_model.get_image_features(**inputs)
        except Exception as e:
            return None
    if inputs is not None:
        feat = feat / feat.norm(p=2, dim=-1, keepdim=True)
        return feat[0].detach().numpy().tolist()
    return None


class SystemManager:
    def __init__(self):
        self.client = client
        self.r_cache = []
        self.r_ranks = {}
        # HNSW 立体结构参数
        self.max_level = 3
        self.m_neighbors = 5
        self.interaction_mgr = InteractionManager()
        self.crawler = crawler
        
        # Initialize Gemini Model
        print("🧠 Initializing Gemini API...")
        self.model = genai.GenerativeModel('gemini-pro')
        
        self._init_collections()
        self._ensure_indices()

    def _init_collections(self):
        """初始化 Qdrant 集合"""
        for name in [SPACE_X, SPACE_R]:
            if not self.client.collection_exists(name):
                self.client.create_collection(
                    collection_name=name,
                    vectors_config={
                        "clip": models.VectorParams(size=512, distance=models.Distance.COSINE)
                    }
                )
                print(f"✅ Collection {name} created successfully!")

    def _ensure_indices(self):
        """Ensure necessary payload indices exist."""
        try:
            self.client.create_payload_index(
                collection_name=SPACE_X,
                field_name="url",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            print(f"✅ Index ensured for {SPACE_X}: url")
        except Exception as e:
            # Index might already exist
            pass
            
        try:
            self.client.create_payload_index(
                collection_name=SPACE_R,
                field_name="url",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            print(f"✅ Index ensured for {SPACE_R}: url")
        except Exception as e:
            pass
            
        try:
            self.client.create_payload_index(
                collection_name=SPACE_X,
                field_name="is_summarized",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            print("✅ Index ensured for tum_space_x: is_summarized")
        except Exception:
            pass

    def get_text_embedding(self, text):
        """Wrapper for global get_embedding function."""
        return get_embedding(text=text)

    def trigger_global_recalculation(self):
        """触发基于 HNSW 结构的立体 PageRank 计算"""
        print("\n⚡️ Triggering 3D Network Recalculation (HNSW-based Recalculation) ⚡️")

        # 1. 拉取 R 空间数据
        r_points = []
        offset = None
        while True:
            batch, offset = client.scroll(collection_name=SPACE_R, limit=100, with_vectors=True, offset=offset)
            r_points.extend(batch)
            if offset is None: break

        if not r_points:
            print("   ⚠️ Space R is empty, no calculation needed.")
            return

        self.r_cache = r_points
        print(f"   -> Space R Total Nodes: {len(r_points)}")

        # 2. 构建立体图并计算 PR
        self._calculate_hnsw_pagerank(r_points)

        # 3. 更新 Space X (投影)
        self._update_space_x_scores()

    def _calculate_hnsw_pagerank(self, points):
        """
        构建 HNSW 立体分层图并计算 PageRank (Rust Accelerated)
        """
        try:
            import visual_rank_engine
        except ImportError:
            print("❌ Error: visual_rank_engine not found. Please build the Rust extension.")
            return

        n = len(points)
        if n == 0: return
        
        print(f"   ⚡️ Rust Engine: Calculating PageRank for {n} nodes...")
        start_time = time.time()

        # 1. Prepare Data
        # Ensure IDs are strings
        ids = [str(p.id) for p in points]
        vectors = [p.vector['clip'] for p in points]
        
        # Cold start check
        if not self.interaction_mgr.interactions:
            self.interaction_mgr.simulate_cold_start_data(points)

        # Interaction Weights (Fix: Use ID instead of URL)
        interaction_weights = {}
        for p in points:
            w = self.interaction_mgr.get_interaction_weight(str(p.id))
            interaction_weights[str(p.id)] = w
            
        # Transitions (Convert defaultdict to dict for safety)
        # InteractionManager.transitions is defaultdict(lambda: defaultdict(int))
        transitions = {k: dict(v) for k, v in self.interaction_mgr.transitions.items()}

        # 2. Call Rust
        try:
            ranks = visual_rank_engine.calculate_hnsw_pagerank(
                ids,
                vectors,
                interaction_weights,
                transitions,
                self.m_neighbors,
                0.85, # damping
                30    # iterations
            )
            
            self.r_ranks = ranks
            print(f"   -> ✅ Rust calculation finished in {time.time() - start_time:.4f}s")
            
        except Exception as e:
            print(f"   ❌ Rust Engine Failed: {e}")
            import traceback
            traceback.print_exc()

    def _check_novelty(self, vector):
        """
        独特性检测：计算向量与 R 空间中最近锚点的距离。
        返回: (is_novel, min_distance)
        """
        if not self.r_cache:
            # 如果 R 为空，第一个进来的肯定是新的
            return True, 1.0

        r_vecs = np.array([p.vector['clip'] for p in self.r_cache])
        # 计算与现有锚点的相似度
        sims = np.dot(r_vecs, np.array(vector))
        max_sim = np.max(sims)
        min_dist = 1.0 - max_sim

        is_novel = min_dist > NOVELTY_THRESHOLD
        return is_novel, min_dist

    def process_url_and_add(self, url, trigger_recalc=True, check_db_first=True):
        """
        全自动流水线：检查数据库 -> 爬取（如需要）-> 清洗(熵) -> 向量化 -> 独特性检测 -> 晋升/入库
        Args:
            url: 目标 URL
            trigger_recalc: 是否立即触发全局重算 (批量导入时建议设为 False)
            check_db_first: 是否先检查数据库，如果存在则跳过爬取
        """
        print(f"\n🤖 Processing URL: {url}")
        
        # 0. 检查数据库（如果启用）
        if check_db_first:
            if self.check_url_exists(url, SPACE_X):
                print(f"   ✅ URL已在数据库中，跳过爬取: {url}")
                # 返回数据库中已有的数据信息
                existing_data = self.get_url_from_db(url, SPACE_X)
                if existing_data:
                    print(f"   📦 使用已有数据 (ID: {existing_data['id'][:8]}...)")
                    return existing_data
                else:
                    print(f"   ⚠️  数据库中存在但无法获取数据，继续爬取")

        # 1. 爬取
        data = crawler.parse(url)
        if not data:
            print("   ❌ Crawl failed or content filtered")
            return

        print(f"   -> ✅🐛🕸️Crawl successful! Retrieved {len(data['texts'])} valid text blocks (Entropy Cleaned).")

        promoted_count = 0

        # 2. 处理文本
        for text in data['texts']:
            vec = get_embedding(text=text)
            if not vec: continue

            # --- 独特性检测 ---
            is_novel, dist = self._check_novelty(vec)
            promotion_status = False

            if is_novel:
                # 只有足够独特的知识才会被晋升到 R 空间
                print(f"   🌟 [NOVELTY DETECTED] New knowledge found (Distance {dist:.3f} > {NOVELTY_THRESHOLD}) -> Promoted to Space R")
                print(f"      Content Summary: {text[:40]}...")

                pt_id = str(uuid.uuid4())
                client.upsert(
                    collection_name=SPACE_R,
                    points=[models.PointStruct(id=pt_id, vector={"clip": vec}, payload={"content": text, "url": url})]
                )
                promotion_status = True
                promoted_count += 1
                
                # 如果开启了实时重算
                if trigger_recalc:
                    self.trigger_global_recalculation()

            # 无论如何，都要添加到 X (搜索池)
            payload = {"url": url, "type": "text", "content_preview": text[:100], "pr_score": 0.0}
            
            # 如果有链接信息，存储到payload中
            if 'links' in data and data['links']:
                payload['links'] = data['links'][:50]  # 存储前50个链接
            
            client.upsert(
                collection_name=SPACE_X,
                points=[models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector={"clip": vec},
                    payload=payload
                )]
            )

        print(f"   ✅ URL processing complete. {promoted_count} items promoted to Anchors.")

    def add_to_space_x(self, text, url=None, promote_to_r=False, is_summarized=False, **kwargs):
        """
        添加内容到 Space X (海量信息库)
        
        Args:
            text: 文本内容
            url: URL地址
            promote_to_r: 是否强制晋升到Space R
            is_summarized: 是否已摘要
            **kwargs: 其他参数，包括:
                - full_text: 完整原文
                - links: 链接列表（用于数据库缓存优化）
        """
        if not text: return
        
        print(f"📥 Adding content to Space X: {url or 'Text Upload'}")

        # 1. 生成向量 (CLIP Text Encoder)
        vec = self.get_text_embedding(text)
        if not vec: return

        # 2. 构造 payload
        payload = {
            "url": url,
            "type": "text",
            "content": text,
            "full_text": kwargs.get("full_text", text), # Store original text
            "content_preview": text[:100],
            "pr_score": 0.0,
            "is_summarized": is_summarized
        }
        
        # 如果有链接信息，存储到payload中（用于数据库缓存优化）
        if 'links' in kwargs and kwargs['links']:
            payload['links'] = kwargs['links'][:50]  # 存储前50个链接

        # 3. 插入到 X
        pt_id = str(uuid.uuid4())
        client.upsert(
            collection_name=SPACE_X,
            points=[models.PointStruct(id=pt_id, vector={"clip": vec}, payload=payload)]
        )
        print(f"   ✅ Added to Space X (ID: {pt_id})")

        # 4. (可选) 晋升到 R
        if promote_to_r:
            print("   -> 🚀 Force promotion to Space R")
            client.upsert(
                collection_name=SPACE_R,
                points=[models.PointStruct(id=pt_id, vector={"clip": vec}, payload=payload)]
            )
            self.trigger_global_recalculation()

    def _update_space_x_scores(self):
        # 简单的投影更新逻辑
        if not self.r_cache: return

        # 这里为了演示不打印太多刷屏
        # print("   -> Updating Space X scores (projection calculation)...")

        r_vecs = np.array([p.vector['clip'] for p in self.r_cache])
        r_scores = np.array([self.r_ranks[p.id] for p in self.r_cache])

        offset = None
        while True:
            batch, offset = client.scroll(collection_name=SPACE_X, limit=50, with_vectors=True, offset=offset)
            if not batch: break

            points_to_update = []
            for point in batch:
                x_vec = np.array(point.vector['clip'])
                sims = np.dot(r_vecs, x_vec)
                sims[sims < 0] = 0
                new_score = float(np.sum(sims * r_scores))

                points_to_update.append(models.PointStruct(
                    id=point.id, vector={"clip": x_vec.tolist()},
                    payload={**point.payload, "pr_score": new_score}
                ))
            client.upsert(collection_name=SPACE_X, points=points_to_update)
            if offset is None: break

    # ... (保留之前的 __init__, trigger_global_recalculation 等所有代码) ...

    # [新增] 分页浏览接口 (用于 Admin 面板)
    def browse_collection(self, collection_name, limit=50, offset_id=None):
        """
        浏览数据库内容。
        Qdrant 的 scroll API 使用 offset 指针。
        """
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False,  # 浏览时不需要看巨大的向量数据
            offset=offset_id
        )

        results = []
        for p in points:
            results.append({
                "id": p.id,
                "payload": p.payload,
                "score": p.payload.get("pr_score", 0.0)
            })

        return {
            "items": results,
            "next_offset": next_offset
        }

    def check_url_exists(self, url: str, collection_name: str = SPACE_X) -> bool:
        """
        检查URL是否已经在数据库中存在
        
        Args:
            url: 要检查的URL
            collection_name: 要查询的集合名称（默认SPACE_X）
            
        Returns:
            bool: 如果URL存在返回True，否则返回False
        """
        try:
            points, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="url",
                            match=models.MatchValue(value=url)
                        )
                    ]
                ),
                limit=1
            )
            return len(points) > 0
        except Exception as e:
            print(f"⚠️ Error checking URL existence: {e}")
            return False
    
    def get_url_from_db(self, url: str, collection_name: str = SPACE_X) -> Optional[Dict]:
        """
        从数据库获取URL的数据（如果存在）
        
        Args:
            url: 要查询的URL
            collection_name: 要查询的集合名称（默认SPACE_X）
            
        Returns:
            Dict: 包含id和payload的字典，如果不存在返回None
        """
        try:
            points, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="url",
                            match=models.MatchValue(value=url)
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=True
            )
            if points:
                return {
                    'id': points[0].id,
                    'payload': points[0].payload,
                    'vector': points[0].vector
                }
            return None
        except Exception as e:
            print(f"⚠️ Error getting URL from DB: {e}")
            return None
    
    def batch_check_urls(self, urls: List[str], collection_name: str = SPACE_X) -> Dict[str, bool]:
        """
        批量检查多个URL是否存在
        
        Args:
            urls: URL列表
            collection_name: 要查询的集合名称（默认SPACE_X）
            
        Returns:
            Dict[str, bool]: URL到存在性的映射字典
        """
        result = {}
        
        # 批量查询以提高效率
        for url in urls:
            result[url] = self.check_url_exists(url, collection_name)
        
        return result

    # [新增] 删除接口 (用于 Admin 面板)
    def delete_item(self, collection_name, point_id):
        client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=[point_id])
        )
        print(f"🗑️ Deleted ID from {collection_name}: {point_id}")
        # 如果删的是 R 空间，必须触发重算
        if collection_name == SPACE_R:
            self.trigger_global_recalculation()

    # [新增] 从 X 复制到 R (用于 Admin 手动优化)
    def promote_from_x_to_r(self, point_id):
        # 1. 先从 X 拿数据
        points = client.retrieve(
            collection_name=SPACE_X,
            ids=[point_id],
            with_vectors=True,
            with_payload=True
        )
        if not points: return False

        point = points[0]

        # 2. 写入 R
        client.upsert(
            collection_name=SPACE_R,
            points=[models.PointStruct(
                id=point.id,  # 保持 ID 一致
                vector=point.vector,
                payload={**point.payload, "promoted_by_admin": True}
            )]
        )
        print(f"⬆️ Admin manually promoted ID: {point_id}")

        # 3. 触发重算
        self.trigger_global_recalculation()
        return True


    def summarize_text_api(self, text):
        """Use Gemini API to summarize text."""
        if not GOOGLE_API_KEY:
            return text
            
        try:
            # Enforce 200 word limit and ignore child page content
            prompt = f"Please summarize the following content in strictly under 200 words. Focus ONLY on the main content of the current page. Ignore any lists of sub-pages, navigation menus, or teasers for other articles. Make it concise:\n\n{text[:15000]}"
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"⚠️ API Summarization failed: {e}")
            return text

    def backfill_summaries(self, force=False):
        """Iterate through all items in Space X and summarize."""
        print(f"🔄 Starting backfill of summaries (Force={force})...")
        offset = None
        count = 0
        while True:
            batch, offset = self.client.scroll(
                collection_name=SPACE_X, 
                limit=50, 
                with_payload=True, 
                with_vectors=True,
                offset=offset
            )
            if not batch: break
            
            points_to_update = []
            for point in batch:
                payload = point.payload
                
                # If already summarized and not forced, skip
                if payload.get("is_summarized") and not force:
                    continue
                
                # Use full_text if available, otherwise try to extract from content
                full_text = payload.get("full_text", "")
                if not full_text:
                    if "Original Content:" in content:
                        parts = content.split("Original Content:\n")
                        if len(parts) > 1:
                            full_text = parts[1].strip()
                    else:
                        full_text = content

                if not full_text or len(full_text) < 100:
                    continue
                    
                print(f"   📝 Summarizing item: {payload.get('url')}")
                summary = self.summarize_text_api(full_text)
                
                # Update payload
                new_payload = payload.copy()
                new_payload["content"] = summary # Store ONLY summary
                new_payload["full_text"] = full_text # Ensure full_text is preserved
                new_payload["is_summarized"] = True
                
                points_to_update.append(models.PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload=new_payload
                ))
                count += 1
                
            if points_to_update:
                self.client.upsert(collection_name=SPACE_X, points=points_to_update)
                
            if offset is None: break
            
        print(f"✅ Backfill complete. Updated {count} items.")

    def process_url_recursive(self, start_url, max_depth=1, callback=None, check_db_first=True):
        """
        Recursively crawl and process URLs up to max_depth.
        callback(count, url): function to call on successful addition.
        check_db_first: 是否先检查数据库，如果URL已存在则跳过爬取
        """
        print(f"🕸️ Starting recursive crawl: {start_url} (Depth: {max_depth})")
        if check_db_first:
            print(f"   ✅ 已启用数据库检查，将跳过已存在的URL")
        
        visited = set()
        queue = [(start_url, 0)]
        
        # 批量检查URL是否存在（用于优化）
        urls_to_check = [] # (url, depth)
        count = 0
        
        while queue:
            current_url, depth = queue.pop(0)
            
            if current_url in visited:
                continue
            visited.add(current_url)
            
            # 检查数据库（如果启用）
            if check_db_first:
                if self.check_url_exists(current_url, SPACE_X):
                    print(f"   ⏭️  跳过（数据库中已存在）: {current_url}")
                    count += 1
                    if callback:
                        callback(count, current_url)
                    # 尝试从数据库中获取链接信息
                    if depth < max_depth:
                        from urllib.parse import urlparse
                        start_domain = urlparse(start_url).netloc
                        existing_data = self.get_url_from_db(current_url, SPACE_X)
                        if existing_data and 'links' in existing_data.get('payload', {}):
                            # 如果数据库中有链接信息，使用它们
                            stored_links = existing_data['payload'].get('links', [])
                            for link in stored_links:
                                if urlparse(link).netloc == start_domain:
                                    if link not in visited:
                                        queue.append((link, depth + 1))
                            continue  # 跳过爬取，直接使用存储的链接
                        else:
                            # 如果没有存储链接，仍然需要爬取以获取链接
                            # 但可以设置一个标志，只爬取链接，不更新数据库
                            pass  # 继续爬取
            
            # Process current URL
            try:
                # 1. Crawl
                data = self.crawler.parse(current_url)
                if not data:
                    continue
                    
                # 2. Add to DB (Space X)
                # Combine texts for content
                raw_content = "\n\n".join(data['texts'])
                if not raw_content:
                    continue
                
                # Summarize using API
                final_content = raw_content
                is_summarized = False
                
                if len(raw_content) > 300:
                    summary = self.summarize_text_api(raw_content)
                    if summary != raw_content:
                        # ONLY store the summary to keep it clean
                        final_content = summary
                        is_summarized = True
                        print(f"   ✨ API Summarized content for {current_url}")
                    
                # 保存数据时也保存链接信息（用于后续优化）
                self.add_to_space_x(
                    text=final_content, 
                    url=current_url, 
                    promote_to_r=False, 
                    is_summarized=is_summarized, 
                    full_text=raw_content,
                    links=data.get('links', [])  # 传递链接信息
                )
                count += 1
                
                # Trigger callback
                if callback:
                    callback(count, current_url)
                
                # 3. Enqueue children if depth allows
                if depth < max_depth:
                    # Filter links to stay on same domain or be relevant?
                    # For now, let's stick to same domain to avoid exploding
                    from urllib.parse import urlparse
                    start_domain = urlparse(start_url).netloc
                    
                    for link in data.get('links', []):
                        if urlparse(link).netloc == start_domain:
                            if link not in visited:
                                queue.append((link, depth + 1))
                                
            except Exception as e:
                print(f"⚠️ Error processing {current_url}: {e}")
                
        print(f"✅ Recursive crawl finished. Processed {count} pages.")
        return count


# --- 模拟测试 ---
if __name__ == "__main__":
    mgr = SystemManager()

    print("\n🧪 Injecting mock data to verify Rust Engine...")
    # Inject some mock data into Space R to trigger calculation
    mock_vec = [0.1] * 512
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    id3 = str(uuid.uuid4())
    
    mgr.client.upsert(
        collection_name=SPACE_R,
        points=[
            models.PointStruct(id=id1, vector={"clip": mock_vec}, payload={"url": "http://a.com", "content": "A"}),
            models.PointStruct(id=id2, vector={"clip": mock_vec}, payload={"url": "http://b.com", "content": "B"}),
            models.PointStruct(id=id3, vector={"clip": mock_vec}, payload={"url": "http://c.com", "content": "C"}),
        ]
    )
    
    # Add interactions to verify weight passing
    mgr.interaction_mgr.record_interaction(id1, "click")
    
    # Trigger Recalculation
    mgr.trigger_global_recalculation()