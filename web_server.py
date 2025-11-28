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

# 引入核心模块
from system_manager import SystemManager, SPACE_R, SPACE_X
from search_engine import search

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
    print(f"⏳ [AsyncTask] 开始处理任务: {task_type}")

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
            
            # Run recursive crawl
            mgr.process_url_recursive(url, max_depth=1, callback=lambda c, u: asyncio.run(progress_callback(c, u)))
            
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
        print("✅ [AsyncTask] 通知已发送。")

    except Exception as e:
        print(f"❌ [AsyncTask] Error: {e}")
        import traceback
        traceback.print_exc()
        asyncio.run(ws_manager.broadcast({
            "type": "error",
            "message": f"Processing failed: {str(e)}"
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
        return FileResponse('static/index.html')

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
    async def upload_url(url: str = Form(...), background_tasks: BackgroundTasks = None):
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