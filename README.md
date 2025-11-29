---
title: PageRank Search
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# TUM Search Engine & Knowledge Graph

A specialized search engine and knowledge graph system for the Technical University of Munich (TUM).

## Features

*   **Recursive Crawling**: Automatically crawls TUM websites to extract content.
*   **Intelligent Summarization**: Uses Google Gemini API to generate concise (200-word) summaries of crawled pages.
*   **Vector Search**: Uses Qdrant and CLIP embeddings for semantic search.
*   **Knowledge Graph**: Builds a graph of connected concepts (Space X -> Space R promotion mechanism).
*   **Real-time Updates**: WebSocket-based UI for real-time crawling progress.

## Setup

1.  Install dependencies:
    ```bash
    # 方法1: 使用安装脚本（推荐）
    bash install_deps.sh
    
    # 方法2: 手动安装
    pip install -r requirements.txt
    
    # 方法3: 只安装Wiki Dump功能所需依赖
    pip install mwxml mwparserfromhell fastapi uvicorn python-multipart qdrant-client python-dotenv
    
    # 验证安装
    python3 check_dependencies.py
    ```
    
    **注意**: Wiki Dump上传功能需要额外的依赖：
    - `mwxml` - MediaWiki XML dump解析
    - `mwparserfromhell` - Wikicode解析
    
    如果安装失败，请查看 `INSTALL_DEPENDENCIES.md` 获取详细说明。

2.  Configure environment variables in `.env`:
    ```bash
    QDRANT_URL=...
    QDRANT_API_KEY=...
    GOOGLE_API_KEY=...
    ```

3.  Run the server:
    ```bash
    python3 web_server.py --mode user
    ```

## Usage

*   **Search**: Use the search bar to find information.
*   **Add Content**: Use the "Add URL" button to crawl new pages.
*   **Admin Tools**:
    *   `scripts/clear_x.py`: Clear the database.
    *   `scripts/regenerate_summaries.py`: Re-generate summaries using stored content.
