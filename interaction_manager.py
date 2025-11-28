import json
import os
import time
import random
from collections import defaultdict

class InteractionManager:
    def __init__(self, storage_path="interaction_data.json"):
        self.storage_path = storage_path
        self.interactions = defaultdict(lambda: {"clicks": 0, "impressions": 0, "last_active": 0})
        # transitions[source_id][target_id] = count
        self.transitions = defaultdict(lambda: defaultdict(int))
        self.load()

    def load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for k, v in data.get("interactions", {}).items():
                        self.interactions[k] = v
                    
                    # Load transitions
                    trans_data = data.get("transitions", {})
                    for src, targets in trans_data.items():
                        for tgt, count in targets.items():
                            self.transitions[src][tgt] = count
                            
                print(f"📊 Interaction data loaded. {len(self.interactions)} items, {len(self.transitions)} sources.")
            except Exception as e:
                print(f"⚠️ Failed to load interaction data: {e}")

    def save(self):
        try:
            data = {
                "interactions": self.interactions,
                "transitions": self.transitions
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save interaction data: {e}")

    def record_interaction(self, item_id, action_type="click", source_id=None):
        """
        Record a user interaction.
        """
        if not item_id: return
        
        self.interactions[item_id]["last_active"] = time.time()
        
        if action_type == "click":
            self.interactions[item_id]["clicks"] += 1
            
            # Record transition if source is known
            if source_id:
                self.transitions[source_id][item_id] += 1
                
        elif action_type == "impression":
            self.interactions[item_id]["impressions"] += 1
            
        # Auto-save occasionally (in prod this would be async or DB)
        if random.random() < 0.1: 
            self.save()

    def get_transition_weight(self, source_id, target_id):
        """
        Calculate transition boost.
        If users frequently go Source -> Target, this returns > 1.0.
        """
        if not source_id or not target_id:
            return 1.0
            
        transitions = self.transitions.get(source_id, {})
        count = transitions.get(target_id, 0)
        
        if count == 0:
            return 1.0
            
        # Boost formula: 1 + log(1 + count)
        # 1 transition -> 1.3
        # 10 transitions -> 3.3
        return 1.0 + (0.5 * count)

    def get_top_transitions(self, source_id, limit=3):
        """
        Get the most frequent transition targets for a given source.
        Returns a list of (target_id, count) tuples.
        """
        if not source_id:
            return []
            
        targets = self.transitions.get(source_id, {})
        if not targets:
            return []
            
        # Sort by count descending
        sorted_targets = sorted(targets.items(), key=lambda x: x[1], reverse=True)
        return sorted_targets[:limit]

    def get_interaction_weight(self, item_id):
        """
        Calculate a weight boost based on interactions.
        Base weight is 1.0.
        """
        data = self.interactions.get(item_id)
        if not data:
            return 1.0
        
        clicks = data["clicks"]
        # Simple logarithmic boost: 1 + log(1 + clicks)
        # 0 clicks -> 1.0
        # 10 clicks -> ~3.3
        # 100 clicks -> ~5.6
        return 1.0 + (0.5 * clicks) # Linear for stronger effect in demo

    def simulate_cold_start_data(self, items):
        """
        Generate plausible synthetic data for cold start.
        """
        print("🧊 Generating Cold Start Interaction Data...")
        count = 0
        for item in items:
            item_id = item.id
            payload = item.payload
            content = payload.get('content', '').lower()
            url = payload.get('url', '').lower()
            
            # Heuristic: "Degree", "Program", "Research" are popular
            clicks = 0
            if "degree" in url or "program" in url:
                clicks += random.randint(5, 20)
            if "research" in content:
                clicks += random.randint(2, 10)
            if "engineering" in content:
                clicks += random.randint(3, 15)
                
            if clicks > 0:
                self.interactions[item_id]["clicks"] = clicks
                self.interactions[item_id]["last_active"] = time.time()
                count += 1
                
        self.save()
        print(f"🧊 Cold start data generated for {count} items.")

    def get_trending_items(self, limit=5):
        """
        Get items with the highest number of clicks.
        """
        # Sort interactions by clicks descending
        sorted_items = sorted(
            self.interactions.items(), 
            key=lambda x: x[1].get("clicks", 0), 
            reverse=True
        )
        
        # Return top N item_ids
        return [item_id for item_id, data in sorted_items[:limit]]
