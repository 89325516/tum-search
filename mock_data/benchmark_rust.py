import time
import random
import math
import sys
import os

# Avoid importing the local 'visual_rank_engine' directory
# We want the installed package from maturin
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir in sys.path:
    sys.path.remove(current_dir)
if '' in sys.path:
    sys.path.remove('')

import visual_rank_engine

def calculate_temporal_pagerank_python(num_nodes, edges, last_interaction_times, damping, decay_lambda, iterations):
    # Build adjacency list
    adj_out = [[] for _ in range(num_nodes)]
    for src, dst in edges:
        if src < num_nodes and dst < num_nodes:
            adj_out[src].append(dst)
    
    ranks = [1.0 / num_nodes] * num_nodes
    
    for _ in range(iterations):
        new_ranks = [0.0] * num_nodes
        for u in range(num_nodes):
            neighbors = adj_out[u]
            if not neighbors:
                continue
            
            time_factor = math.exp(-decay_lambda * last_interaction_times[u])
            share = (damping * ranks[u] * time_factor) / len(neighbors)
            
            for v in neighbors:
                new_ranks[v] += share
        
        sum_rank = sum(new_ranks)
        if sum_rank > 0:
            ranks = [r / sum_rank for r in new_ranks]
        else:
            ranks = [1.0 / num_nodes] * num_nodes # Reset if all zero (shouldn't happen usually)
            
    return ranks

def run_benchmark():
    print("Generating synthetic data...")
    num_nodes = 50000
    num_edges = 500000
    edges = []
    for _ in range(num_edges):
        edges.append((random.randint(0, num_nodes-1), random.randint(0, num_nodes-1)))
    
    last_interactions = [random.uniform(0, 72) for _ in range(num_nodes)]
    
    damping = 0.85
    decay = 0.01
    iterations = 50
    
    print(f"Running benchmark with {num_nodes} nodes, {num_edges} edges, {iterations} iterations.")
    
    # Python Benchmark
    print("Starting Python benchmark...")
    start_time = time.time()
    calculate_temporal_pagerank_python(num_nodes, edges, last_interactions, damping, decay, iterations)
    python_time = time.time() - start_time
    print(f"Python Time: {python_time:.4f}s")
    
    # Rust Benchmark
    print("Starting Rust benchmark...")
    start_time = time.time()
    visual_rank_engine.calculate_temporal_pagerank(num_nodes, edges, last_interactions, damping, decay, iterations)
    rust_time = time.time() - start_time
    print(f"Rust Time:   {rust_time:.4f}s")
    
    if rust_time > 0:
        print(f"Speedup:     {python_time / rust_time:.2f}x")

if __name__ == "__main__":
    run_benchmark()
