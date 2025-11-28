import requests
import time
import random
from system_manager import SystemManager, SPACE_X
from search_engine import search

def simulate_navigation_flow():
    print("🚀 Starting Navigation Flow Simulation...")
    
    # 1. Search for "Engineering" to find a starting point
    print("\n[Step 1] User searches for 'Engineering'...")
    results = search("Engineering", top_k=10)
    
    if not results:
        print("❌ No results found.")
        return

    # Let's pick a "Source" page (e.g., Rank 1) and a "Target" page (e.g., Rank 3)
    source_item = results[0]
    target_item = results[2] if len(results) > 2 else results[1]
    
    source_url = source_item['url']
    target_url = target_item['url']
    
    print(f"📍 Source Page: {source_url}")
    print(f"🎯 Target Page: {target_url}")
    print(f"   Target Initial Score: {target_item['score']:.4f}")
    
    # 2. Simulate User Navigation: Source -> Target
    # This means users are reading Source, seeing a link to Target, and clicking it.
    # This implies Source "trusts" Target.
    
    print(f"\n[Step 2] Simulating 30 users navigating from Source -> Target...")
    
    mgr = SystemManager()
    
    for i in range(30):
        # Record transition: Source -> Target
        mgr.interaction_mgr.record_interaction(target_url, "click", source_id=source_url)
        if i % 10 == 0:
            print(f"   - Transition {i+1} recorded.")
            
    mgr.interaction_mgr.save()
    
    # 3. Trigger Recalculation
    print("\n[Step 3] Triggering Global Recalculation...")
    mgr.trigger_global_recalculation()
    
    # 4. Check Results
    print("\n[Step 4] Searching again...")
    new_results = search("Engineering", top_k=10)
    
    new_target_score = 0
    new_target_rank = -1
    
    for i, res in enumerate(new_results):
        if res['url'] == target_url:
            new_target_score = res['score']
            new_target_rank = i + 1
            break
            
    print(f"\n📊 Result Analysis:")
    print(f"   Target: {target_url}")
    print(f"   Old Score: {target_item['score']:.4f}")
    print(f"   New Score: {new_target_score:.4f}")
    print(f"   New Rank:  #{new_target_rank}")
    
    if new_target_score > target_item['score']:
        print("✅ SUCCESS: Target score increased due to transitive trust!")
    else:
        print("⚠️ WARNING: Score did not increase.")

if __name__ == "__main__":
    simulate_navigation_flow()
