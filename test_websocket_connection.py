#!/usr/bin/env python3
"""
测试WebSocket连接和消息发送
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket!")
            
            # 等待几秒看看是否能收到消息
            print("Waiting for messages (5 seconds)...")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received message: {message}")
                data = json.loads(message)
                print(f"Parsed data: {data}")
            except asyncio.TimeoutError:
                print("⚠️ No messages received in 5 seconds")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_websocket())
