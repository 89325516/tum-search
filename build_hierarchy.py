import pickle
import numpy as np
import sys
import os

# Add root to path to import hierarchy_engine
sys.path.append(os.getcwd())
from hierarchy_engine import HierarchicalIndex

def build_index():
    print("🏗️ Loading Anchor Data...")
    try:
        with open('mock_data/anchors.pkl', 'rb') as f:
            anchors = pickle.load(f)
    except FileNotFoundError:
        print("❌ mock_data/anchors.pkl not found. Please run prepare_anchors.py first.")
        return

    print(f"   - Loaded {len(anchors)} anchors.")
    
    vectors = []
    ids = []
    payloads = []
    
    for i, anchor in enumerate(anchors):
        # anchor structure: {'id': ..., 'vector': ..., 'pr_score': ..., 'payload': ...}
        vectors.append(anchor['vector'])
        # If ID is missing, use index
        ids.append(anchor.get('id', i))
        
        # Construct payload
        p = {
            "pr_score": anchor.get('pr_score', 0.0),
            "url": anchor.get('url', '#'),
            "type": anchor.get('type', 'unknown'),
            "content_preview": anchor.get('content_preview', '')
        }
        payloads.append(p)
        
    # Build Index
    # Adjust clusters based on data size
    # If we have 10k items: L2=100, L1=10 is good.
    # If we have small mock data (e.g. 100 items), we need smaller clusters.
    n_samples = len(vectors)
    l2_k = min(100, int(np.sqrt(n_samples)))
    l1_k = 10
    
    if l2_k < 2: l2_k = 2 # Minimum 2 clusters
    
    print(f"   - Config: Layer2={l2_k}, Layer1={l1_k}")
    
    index = HierarchicalIndex(layer2_clusters=l2_k, layer1_clusters=l1_k)
    index.build(vectors, ids, payloads)
    
    # Save
    out_path = 'mock_data/hierarchical_index.pkl'
    index.save(out_path)
    print(f"✅ Index saved to {out_path}")

if __name__ == "__main__":
    build_index()
