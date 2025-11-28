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
    pip install -r requirements.txt
    ```

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
