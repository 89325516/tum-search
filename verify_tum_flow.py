import sys
import os
from system_manager import SystemManager
from search_engine import search

def verify_tum_flow():
    url = "https://www.tum.de/en/studies/degree-programs"
    print(f"🚀 Starting verification for URL: {url}")
    
    # 1. Initialize System Manager
    mgr = SystemManager()
    
    # 2. Process URL (Crawl -> Ingest -> Promote?)
    print("\n[Step 1] Processing URL...")
    mgr.process_url_and_add(url)
    
    # 3. Search for "Engineering"
    query = "Engineering"
    print(f"\n[Step 2] Searching for '{query}'...")
    results = search(query, top_k=10)
    
    # 4. Verify Results
    print(f"\n[Step 3] Verifying results...")
    found = False
    for i, res in enumerate(results):
        print(f"Rank {i+1}: {res['url']} (Score: {res['score']:.4f})")
        if url in res['url'] or "tum.de" in res['url']:
            found = True
            print("   ✅ Found TUM content!")
            
    if found:
        print("\n✅ Verification SUCCESS: TUM content was crawled and found in search results.")
    else:
        print("\n❌ Verification FAILED: TUM content not found in top results.")

if __name__ == "__main__":
    verify_tum_flow()
