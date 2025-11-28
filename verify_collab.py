import requests
import time
import random
from system_manager import SystemManager, SPACE_X
from search_engine import search

def verify_collaborative_filtering():
    print("🚀 Starting Collaborative Filtering Verification...")
    
    # 1. Search for "Engineering" to find a starting point
    print("\n[Step 1] User searches for 'Engineering'...")
    results = search("Engineering", top_k=10)
    
    if len(results) < 3:
        print("❌ Not enough results found.")
        return

    # Pick Source (A) and a semantically unrelated Target (X)
    # Since we don't have truly unrelated items in this small crawl, we pick the last item.
    source_item = results[0]
    target_item = results[-1] 
    
    source_url = source_item['url']
    target_url = target_item['url']
    source_id = source_item['id']
    
    print(f"📍 Source Page: {source_url}")
    print(f"🎯 Target Page (Simulated 'Unrelated'): {target_url}")
    
    # 2. Simulate User Navigation: Source -> Target
    print(f"\n[Step 2] Simulating 15 users navigating from Source -> Target...")
    
    mgr = SystemManager()
    
    for i in range(15):
        # Record transition: Source -> Target
        mgr.interaction_mgr.record_interaction(target_url, "click", source_id=source_url)
            
    mgr.interaction_mgr.save()
    
    # 3. Check API response for Source Item
    print(f"\n[Step 3] Checking API response for Source Item ID: {source_id}...")
    
    # We need to run this against the running server, but since we are in the same env,
    # we can simulate the logic directly or call the function if we could import it.
    # But web_server.py is a script. Let's just use the logic directly.
    
    top_transitions = mgr.interaction_mgr.get_top_transitions(source_url, limit=3)
    print(f"   Top Transitions from InteractionManager: {top_transitions}")
    
    found = False
    for url, count in top_transitions:
        if url == target_url:
            found = True
            print(f"✅ SUCCESS: Target URL found in top transitions with count {count}")
            break
            
    if not found:
        print("❌ FAILURE: Target URL not found in top transitions.")

if __name__ == "__main__":
    verify_collaborative_filtering()
