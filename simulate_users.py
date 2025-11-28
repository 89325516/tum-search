import requests
import time
import random
from system_manager import SystemManager, SPACE_X
from search_engine import search

def simulate_user_behavior():
    print("🚀 Starting User Simulation...")
    
    # 1. Search for "Engineering"
    print("\n[Step 1] User searches for 'Engineering'...")
    results = search("Engineering", top_k=10)
    
    if not results:
        print("❌ No results found. Cannot simulate clicks.")
        return

    # 2. Pick a target to "boost" (e.g., the 3rd result)
    if len(results) >= 3:
        target_item = results[2]
    else:
        target_item = results[0]
        
    target_id = target_item['id']
    target_url = target_item['url']
    initial_score = target_item['score']
    
    print(f"🎯 Target Item: {target_url} (ID: {target_id})")
    print(f"   Initial Score: {initial_score:.4f}")
    
    # 3. Simulate Clicks
    # Let's say 20 users click this specific result
    print(f"\n[Step 2] Simulating 20 users clicking on this item...")
    
    mgr = SystemManager() # Initialize to access interaction_mgr directly for simulation speed
    # In real life, this would be via API: requests.post("/api/feedback", ...)
    
    for i in range(20):
        # Use URL as key
        mgr.interaction_mgr.record_interaction(target_url, "click")
        if i % 5 == 0:
            print(f"   - Click {i+1} recorded.")
            
    mgr.interaction_mgr.save() # Force save
            
    # 4. Trigger Recalculation
    print("\n[Step 3] Triggering Global Recalculation...")
    mgr.trigger_global_recalculation()
    
    # 5. Search again and check rank
    print("\n[Step 4] Searching for 'Engineering' again...")
    new_results = search("Engineering", top_k=10)
    
    new_rank = -1
    new_score = 0
    for i, res in enumerate(new_results):
        if res['id'] == target_id:
            new_rank = i + 1
            new_score = res['score']
            break
            
    print(f"\n📊 Result Analysis:")
    print(f"   Target: {target_url}")
    print(f"   Old Score: {initial_score:.4f}")
    print(f"   New Score: {new_score:.4f}")
    print(f"   New Rank:  #{new_rank}")
    
    if new_score > initial_score:
        print("✅ SUCCESS: Score increased after user feedback!")
    else:
        print("⚠️ WARNING: Score did not increase. Check weighting logic.")

if __name__ == "__main__":
    simulate_user_behavior()
