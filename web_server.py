from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List
import shutil
import os
import time
import datetime
import asyncio
from qdrant_client import models
import argparse
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 引入核心模块
from system_manager import SystemManager, SPACE_R, SPACE_X
from search_engine import search
from xml_dump_processor import MediaWikiDumpProcessor

# 从环境变量读取爬取密码
CRAWL_PASSWORD = os.getenv("CRAWL_PASSWORD", "")

# 解析命令行参数
parser = argparse.ArgumentParser(description="TUM Search Engine Server")
parser.add_argument("--mode", type=str, choices=["user", "admin"], default="user", help="Server mode: user or admin")
parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
# 避免与 uvicorn 的参数冲突，只解析已知的
args, unknown = parser.parse_known_args()

app = FastAPI(title=f"TUM Search Engine ({args.mode.upper()})")

# 挂载静态文件 (前端页面)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化核心管理器
mgr = SystemManager()


# --- WebSocket 连接管理器 (用于实时通知) ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


ws_manager = ConnectionManager()


# --- 异步后台任务 (耗时操作在这里做) ---
def background_process_content(task_type: str, content: str = None, file_path: str = None, url: str = None):
    """
    后台执行：爬取/入库 -> 独特性检测 -> (可能) HNSW重算 -> 发送通知
    """
    start_time = time.time()
    print(f"⏳ [AsyncTask] Starting task: {task_type}")

    try:
        # 执行具体逻辑
        if task_type == "url":
            # Define callback to send progress via WebSocket
            async def progress_callback(count, current_url):
                await ws_manager.broadcast({
                    "type": "progress",
                    "count": count,
                    "message": f"Processed: {current_url}"
                })
            
            # Run recursive crawl (启用数据库检查以跳过已存在的URL)
            mgr.process_url_recursive(url, max_depth=1, callback=lambda c, u: asyncio.run(progress_callback(c, u)), check_db_first=True)
            
            # Get total count
            total_count = mgr.client.count(collection_name=SPACE_X).count
            
            asyncio.run(ws_manager.broadcast({
                "type": "system_update",
                "message": f"✅ Recursive crawl finished. Processed {total_count} pages in total."
            }))
        elif task_type == "text":
            # 简单文本处理，复用 add_to_space_x
            mgr.add_to_space_x(text=content, url="User Upload", promote_to_r=False)
        elif task_type == "image":
            mgr.add_to_space_x(image_path=file_path, url="User Image Upload", promote_to_r=False)
            # 清理临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
        # 任务完成，准备通知消息
        duration = time.time() - start_time
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构造用户要求的英文通知
        notification_msg = (
            f"Update Completed at {timestamp}. "
            f"The Database (Space X & R) and the Representative Network have been synchronized. "
            f"Search results may vary as the system evolves. "
            f"Processing time: {duration:.2f}s."
        )

        # 通过 WebSocket 广播给所有在线用户
        asyncio.run(ws_manager.broadcast({
            "type": "system_update",
            "message": notification_msg,
            "timestamp": timestamp
        }))
        print("✅ [AsyncTask] Notification sent.")

    except Exception as e:
        print(f"❌ [AsyncTask] Error: {e}")
        import traceback
        traceback.print_exc()
        asyncio.run(ws_manager.broadcast({
            "type": "error",
            "message": f"Processing failed: {str(e)}"
        }))


def background_process_xml_dump(file_path: str, base_url: str = "", max_pages: int = None):
    """
    后台处理XML dump导入任务
    """
    start_time = time.time()
    print(f"⏳ [XML Dump Import] Starting XML dump import from {file_path}")
    
    try:
        # 初始化处理器
        processor = MediaWikiDumpProcessor(
            base_url=base_url,
            wiki_type="auto"  # 自动检测Wiki类型
        )
        
        # 进度回调函数
        def progress_callback(current: int, total: int, message: str):
            progress = int((current / total) * 100) if total > 0 else 0
            asyncio.run(ws_manager.broadcast({
                "type": "progress",
                "count": current,
                "total": total,
                "message": f"XML Dump处理进度: {current}/{total} ({progress}%) - {message}"
            }))
        
        # 处理dump文件
        processor.process_dump(file_path, max_pages=max_pages, progress_callback=progress_callback)
        
        # 导入到数据库
        asyncio.run(ws_manager.broadcast({
            "type": "progress",
            "message": "正在导入数据到数据库..."
        }))
        
        mgr_instance = SystemManager()
        stats = processor.import_to_database(
            mgr_instance,
            url_prefix=base_url or processor.base_url,
            batch_size=50,
            import_edges=False,  # 暂时不通过CSV导入边
            edges_csv_path=None,
            check_db_first=True  # 检查数据库，跳过已存在的URL
        )
        
        # 导入边（链接关系）- 通过生成临时CSV然后导入
        edge_count = 0
        if processor.links:
            asyncio.run(ws_manager.broadcast({
                "type": "progress",
                "message": "正在导入链接关系..."
            }))
            
            # 生成临时边CSV文件
            import tempfile
            import csv
            temp_edges_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
            edges_writer = csv.writer(temp_edges_file)
            edges_writer.writerow(['source_title', 'target_title'])
            
            for source_title, target_titles in processor.links.items():
                for target_title in target_titles:
                    if source_title in processor.pages and target_title in processor.pages:
                        edges_writer.writerow([source_title, target_title])
            
            temp_edges_file.close()
            
            # 使用import_edges模块导入
            try:
                from import_edges import import_edges_from_csv
                url_prefix_for_edges = base_url or processor.base_url
                import_edges_from_csv(temp_edges_file.name, mgr_instance, base_url=url_prefix_for_edges)
                # 计算边的总数
                edge_count = sum(len(target_titles) for target_titles in processor.links.values())
            except Exception as e:
                print(f"⚠️  边导入失败: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # 清理临时文件
                if os.path.exists(temp_edges_file.name):
                    os.remove(temp_edges_file.name)
        
        # 清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # 发送完成通知
        duration = time.time() - start_time
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        success_msg = (
            f"✅ XML Dump导入完成 ({timestamp})\n"
            f"处理页面: {processor.stats['processed_pages']}\n"
            f"总页面: {processor.stats['total_pages']}\n"
            f"成功导入: {stats['success']}\n"
            f"跳过（已存在）: {stats.get('skipped', 0)}\n"
            f"失败: {stats['failed']}\n"
            f"链接关系: {edge_count}\n"
            f"晋升到Space R: {stats['promoted']}\n"
            f"处理时间: {duration:.2f}秒"
        )
        
        asyncio.run(ws_manager.broadcast({
            "type": "system_update",
            "message": success_msg,
            "timestamp": timestamp
        }))
        
        print(f"✅ [XML Dump Import] Completed: {stats['success']} items, {edge_count} edges imported")
        
    except Exception as e:
        print(f"❌ [XML Dump Import] Error: {e}")
        import traceback
        traceback.print_exc()
        
        # 清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)
        
        asyncio.run(ws_manager.broadcast({
            "type": "error",
            "message": f"XML Dump导入失败: {str(e)}"
        }))


# ================= 路由定义 =================

# 1. 通用路由 (User & Admin)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # 保持连接，虽不接收消息
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.get("/api/search")
async def api_search(q: str):
    results = search(q, top_k=20)
    return {"results": results}

@app.get("/api/search/graph")
async def api_search_graph(q: str, max_nodes: int = 30):
    """
    返回搜索结果的网络图数据
    构建以查询结果为中心的节点网络图
    """
    from search_engine import search
    from urllib.parse import urlparse
    
    # 1. 获取搜索结果
    search_results = search(q, top_k=min(10, max_nodes // 3))
    
    if not search_results:
        return {"nodes": [], "edges": []}
    
    # 2. 构建节点和边的集合
    nodes_dict = {}  # id -> node data
    edges_list = []  # List of (source_id, target_id, weight) tuples
    
    # 提取节点标题的辅助函数
    def extract_title(url, content_preview="", node_id=""):
        if url:
            # 提取URL路径的最后一部分
            url_part = url.split('/')[-1].split('?')[0]  # 移除查询参数
            url_part = url_part.replace('_', ' ').replace('-', ' ')
            if url_part and url_part != url:
                title = url_part[:50]
                return title if len(title) <= 50 else title[:47] + "..."
        
        # 如果URL不可用，尝试从内容中提取
        if content_preview:
            words = content_preview.split()[:5]  # 取前5个词
            title = ' '.join(words)[:50]
            return title if len(title) <= 50 else title[:47] + "..."
        
        # 最后使用节点ID
        return f"Node {node_id[:8]}" if node_id else "Unknown Node"
    
    # 3. 为每个搜索结果添加节点，并找到相关节点
    for result in search_results:
        result_id = result['id']
        result_url = result.get('url', '')
        
        node_title = extract_title(result_url, result.get('content', ''), result_id)
        
        # 添加中心节点（搜索结果）
        nodes_dict[result_id] = {
            "id": result_id,
            "name": node_title,
            "url": result_url,
            "content": result.get('content', '')[:100],
            "score": result.get('score', 0.0),
            "category": result.get('type', 'unknown'),
            "value": result.get('score', 0.0) * 100,  # 节点大小
            "isCenter": True  # 标记为中心节点
        }
        
        # 4. 查找相关节点（通过向量相似度）
        try:
            # 从数据库中获取该节点的向量
            points = mgr.client.retrieve(
                collection_name=SPACE_X,
                ids=[result_id],
                with_vectors=True,
                with_payload=True
            )
            
            if points:
                point = points[0]
                
                # 查找相似的节点
                related_hits = mgr.client.query_points(
                    collection_name=SPACE_X,
                    query=point.vector['clip'],
                    using="clip",
                    limit=5  # 每个中心节点最多5个相关节点
                ).points
                
                for hit in related_hits:
                    if hit.id == result_id:
                        continue
                    
                    # 限制节点数量
                    if len(nodes_dict) >= max_nodes:
                        break
                    
                    # 提取相关节点标题
                    related_url = hit.payload.get('url', '')
                    related_content = hit.payload.get('content_preview', '')
                    related_title = extract_title(related_url, related_content, hit.id)
                    
                    # 添加相关节点
                    if hit.id not in nodes_dict:
                        nodes_dict[hit.id] = {
                            "id": hit.id,
                            "name": related_title,
                            "url": related_url,
                            "content": hit.payload.get('content_preview', '')[:100],
                            "score": float(hit.score),
                            "category": hit.payload.get('type', 'unknown'),
                            "value": float(hit.score) * 50,  # 相关节点较小
                            "isCenter": False
                        }
                    
                    # 添加边（中心节点 -> 相关节点）
                    edge_tuple = (result_id, hit.id, float(hit.score))
                    if edge_tuple not in edges_list:
                        edges_list.append(edge_tuple)
        
        except Exception as e:
            print(f"⚠️ Error finding related nodes for {result_id}: {e}")
        
        # 5. 查找协作过滤节点（通过transitions）
        try:
            top_transitions = mgr.interaction_mgr.get_top_transitions(result_id, limit=3)
            
            for target_id, count in top_transitions:
                if len(nodes_dict) >= max_nodes:
                    break
                
                # 如果节点已存在，只添加边
                if target_id not in nodes_dict:
                    try:
                        target_points = mgr.client.retrieve(
                            collection_name=SPACE_X,
                            ids=[target_id],
                            with_payload=True
                        )
                        
                        if target_points:
                            target_point = target_points[0]
                            target_url = target_point.payload.get('url', '')
                            target_content = target_point.payload.get('content_preview', '')
                            target_title = extract_title(target_url, target_content, target_id)
                            
                            nodes_dict[target_id] = {
                                "id": target_id,
                                "name": target_title,
                                "url": target_url,
                                "content": target_point.payload.get('content_preview', '')[:100],
                                "score": 0.5,  # 协作过滤节点中等权重
                                "category": target_point.payload.get('type', 'unknown'),
                                "value": 30.0,
                                "isCenter": False
                            }
                    except Exception:
                        continue
                
                # 添加协作边（权重基于transition count）
                edge_weight = 0.3 + (count * 0.1)  # 基于transition次数
                edge_tuple = (result_id, target_id, edge_weight)
                # 检查是否已存在相同的边，如果存在则更新权重
                existing_edge = next((e for e in edges_list if e[0] == result_id and e[1] == target_id), None)
                if existing_edge:
                    edges_list.remove(existing_edge)
                    edge_weight = max(edge_weight, existing_edge[2])  # 使用较大的权重
                edges_list.append((result_id, target_id, edge_weight))
        
        except Exception as e:
            print(f"⚠️ Error finding collaborative nodes for {result_id}: {e}")
    
    # 6. 转换数据格式
    nodes = list(nodes_dict.values())
    edges = [{"source": src, "target": tgt, "value": weight} for src, tgt, weight in edges_list]
    
    return {
        "nodes": nodes,
        "edges": edges,
        "query": q
    }

@app.post("/api/feedback")
async def api_feedback(item_id: str = Form(...), action: str = Form(...), source_id: str = Form(None)):
    """
    Record user feedback (click, impression, etc.)
    """
    mgr.interaction_mgr.record_interaction(item_id, action, source_id)
    mgr.interaction_mgr.record_interaction(item_id, action, source_id)
    return {"status": "recorded", "item_id": item_id}

@app.get("/api/trending")
async def api_trending(limit: int = 5):
    """
    Get trending items based on clicks.
    """
    trending_ids = mgr.interaction_mgr.get_trending_items(limit)
    print(f"🔥 Trending IDs: {trending_ids}")
    
    results = []
    if trending_ids:
        # Retrieve details from Space X
        try:
            points = mgr.client.retrieve(
                collection_name=SPACE_X,
                ids=trending_ids,
                with_payload=True
            )
        except Exception as e:
            print(f"❌ Error retrieving trending items: {e}")
            return {"results": []}
        
        # Map back to preserve order (retrieve might not preserve order)
        points_map = {p.id: p for p in points}
        
        for tid in trending_ids:
            if tid in points_map:
                p = points_map[tid]
                results.append({
                    "id": p.id,
                    "payload": p.payload,
                    "clicks": mgr.interaction_mgr.interactions[tid]["clicks"]
                })
                
    return {"results": results}

@app.get("/view/{item_id}")
async def view_item(item_id: str):
    return FileResponse('static/view.html')

@app.get("/api/item/{item_id}")
async def get_item_details(item_id: str):
    # 1. Retrieve item from Space X
    points = mgr.client.retrieve(
        collection_name=SPACE_X,
        ids=[item_id],
        with_payload=True,
        with_vectors=True
    )
    if not points:
        raise HTTPException(status_code=404, message="Item not found")
    
    item = points[0]
    
    # 2. Find related items (Internal Navigation Links)
    # Use the item's vector to find similar items
    related_hits = mgr.client.query_points(
        collection_name=SPACE_X,
        query=item.vector['clip'],
        using="clip",
        limit=6 # Top 5 related (excluding self)
    ).points
    
    related = []
    for hit in related_hits:
        if hit.id != item_id:
            related.append({
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            })
            
    # 3. Collaborative Filtering Recommendations (People also visited)
    # Based on transitions from this item
    collab_recs = []
    # Use UUID (item.id) for transitions
    top_transitions = mgr.interaction_mgr.get_top_transitions(item.id, limit=3)
    
    if top_transitions:
        target_ids = [t[0] for t in top_transitions]
        # Retrieve target items by ID
        target_points = mgr.client.retrieve(
            collection_name=SPACE_X,
            ids=target_ids,
            with_payload=True
        )
        
        # Create a map for easy lookup
        target_map = {p.id: p for p in target_points}
        
        for target_id, count in top_transitions:
            if target_id in target_map:
                hit = target_map[target_id]
                collab_recs.append({
                    "id": hit.id,
                    "count": count,
                    "payload": hit.payload
                })

    return {
        "item": {
            "id": item.id,
            "payload": item.payload
        },
        "related": related[:5],
        "collaborative": collab_recs
    }

# 2. 模式特定路由
if args.mode == "user":
    print("🚀 Server starting in USER mode")
    
    @app.get("/")
    async def get_user_ui():
        response = FileResponse('static/index.html')
        # 添加缓存控制头，确保页面更新后能立即看到效果
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.get("/api/feed")
    async def api_feed(limit: int = 20, offset: str = None):
        """
        User Feed: Browse Space X (Public Content) only.
        """
        # 强制指定 SPACE_X，防止用户访问 R
        offset_val = offset if offset and offset != "null" else None
        return mgr.browse_collection(SPACE_X, limit, offset_val)

    # 用户上传接口
    @app.post("/api/admin/backfill")
    async def trigger_backfill(background_tasks: BackgroundTasks, force: bool = False):
        """Trigger background backfill of summaries."""
        background_tasks.add_task(mgr.backfill_summaries, force=force)
        return {"status": "started", "message": f"Backfill process started (Force={force})."}

    @app.post("/api/upload/url")
    async def upload_url(url: str = Form(...), password: str = Form(None), background_tasks: BackgroundTasks = None):
        # 验证密码
        if not CRAWL_PASSWORD:
            raise HTTPException(status_code=500, detail="服务器未配置爬取密码，请联系管理员")
        
        if not password or password != CRAWL_PASSWORD:
            raise HTTPException(status_code=403, detail="密码错误，爬取被拒绝")
        
        # 密码验证通过，开始处理
        background_tasks.add_task(background_process_content, "url", url=url)
        return {"status": "processing", "message": "URL received. Processing..."}

    @app.post("/api/upload/text")
    async def upload_text(text: str = Form(...), background_tasks: BackgroundTasks = None):
        background_tasks.add_task(background_process_content, "text", content=text)
        return {"status": "processing", "message": "Text received. Processing..."}

    @app.post("/api/upload/image")
    async def upload_image(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
        os.makedirs("temp_uploads", exist_ok=True)
        file_path = f"temp_uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        background_tasks.add_task(background_process_content, "image", file_path=file_path)
        return {"status": "processing", "message": "Image received. Processing..."}

    @app.post("/api/upload/xml-dump")
    async def upload_xml_dump(
        file: UploadFile = File(...),
        base_url: str = Form(""),
        max_pages: int = Form(None),
        background_tasks: BackgroundTasks = None
    ):
        """
        上传XML Dump文件（MediaWiki/Wikipedia格式）
        自动解析并导入到数据库，无需借助爬虫
        """
        # 检查文件类型
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith('.xml') or filename_lower.endswith('.xml.bz2') or filename_lower.endswith('.xml.gz')):
            raise HTTPException(status_code=400, detail="只支持XML格式的dump文件（.xml, .xml.bz2, .xml.gz）")
        
        # 保存临时文件
        os.makedirs("temp_uploads", exist_ok=True)
        file_path = f"temp_uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 异步处理XML dump导入
        background_tasks.add_task(
            background_process_xml_dump,
            file_path=file_path,
            base_url=base_url,
            max_pages=max_pages if max_pages else None
        )
        return {"status": "processing", "message": f"XML Dump文件已接收，开始解析和导入..."}


elif args.mode == "admin":
    print("🛡️ Server starting in ADMIN mode")
    
    @app.get("/")
    async def get_admin_ui():
        return FileResponse('static/admin.html')

    # Admin 浏览接口 (可看 X 和 R)
    @app.get("/api/admin/browse")
    async def admin_browse(space: str, limit: int = 50, offset: str = None):
        collection = SPACE_R if space == "R" else SPACE_X
        offset_val = offset if offset and offset != "null" else None
        return mgr.browse_collection(collection, limit, offset_val)

    @app.post("/api/admin/promote")
    async def admin_promote(id: str = Form(...)):
        success = mgr.promote_from_x_to_r(id)
        return {"success": success}

    @app.delete("/api/admin/delete")
    async def admin_delete(space: str, id: str):
        collection = SPACE_R if space == "R" else SPACE_X
        mgr.delete_item(collection, id)
        return {"success": True}


if __name__ == "__main__":
    import uvicorn
    # 使用命令行参数指定的端口
    uvicorn.run(app, host="0.0.0.0", port=args.port)