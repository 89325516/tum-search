import numpy as np
import time
import random
import sys
import os
sys.path.append(os.getcwd())
from hierarchy_engine import HierarchicalIndex


def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0: return v
    return v / norm

def run_verification():
    print("🧪 Starting Verification of Hierarchical Index (HNSW Logic)...")
    
    # 1. Generate Synthetic Data
    N = 50000  # 50k items
    D = 512    # CLIP dimension
    print(f"   - Generating {N} random vectors (dim={D})...")
    
    # Create clusters to make data somewhat realistic (otherwise K-Means struggles)
    # 100 true clusters
    true_centers = np.random.randn(100, D)
    vectors = []
    ids = []
    
    for i in range(N):
        center = true_centers[i % 100]
        noise = np.random.randn(D) * 0.1
        vec = normalize(center + noise)
        vectors.append(vec)
        ids.append(i)
        
    vectors = np.array(vectors)
    
    # 2. Build Hierarchy
    index = HierarchicalIndex(layer2_clusters=100, layer1_clusters=10)
    start_build = time.time()
    index.build(vectors, ids)
    print(f"   - Build Time: {time.time() - start_build:.2f}s")
    
    # 3. Benchmark Search
    num_queries = 100
    print(f"   - Running {num_queries} queries...")
    
    queries = [normalize(np.random.randn(D)) for _ in range(num_queries)]
    
    # Flat Search (Baseline)
    start_flat = time.time()
    flat_comparisons = 0
    for q in queries:
        # Dot product with ALL vectors
        _ = np.dot(vectors, q)
        flat_comparisons += N
    flat_time = time.time() - start_flat
    
    # Hierarchical Search
    start_hier = time.time()
    hier_comparisons = 0
    for q in queries:
        _ = index.search(q, top_k=10, beam_size=3)
        hier_comparisons += index.stats["comparisons"]
    hier_time = time.time() - start_hier
    
    # 4. Report
    print("\n" + "="*40)
    print("      VERIFICATION RESULTS      ")
    print("="*40)
    print(f"Dataset Size: {N}")
    print(f"Queries:      {num_queries}")
    print("-" * 40)
    print(f"Flat Search Time:      {flat_time:.4f}s")
    print(f"Hierarchical Time:     {hier_time:.4f}s")
    print(f"Speedup:               {flat_time / hier_time:.2f}x")
    print("-" * 40)
    print(f"Flat Comparisons:      {flat_comparisons // num_queries} per query")
    print(f"Hierarchical Comps:    {hier_comparisons // num_queries} per query")
    print(f"Reduction Ratio:       {(hier_comparisons / flat_comparisons) * 100:.2f}% (Lower is better)")
    print("="*40)
    
    if (hier_comparisons / flat_comparisons) < 0.05:
        print("✅ SUCCESS: Exponential Optimization Confirmed (< 5% computations)")
    else:
        print("❌ WARNING: Optimization not aggressive enough")

if __name__ == "__main__":
    run_verification()
