# 本代码暂时未使用

# 本代码暂时未使用

import numpy as np
import pickle
import os
from sklearn.cluster import KMeans

class HierarchicalIndex:
    def __init__(self, layer2_clusters=100, layer1_clusters=10):
        """
        Args:
            layer2_clusters: Number of top-level clusters (Strategic Layer).
            layer1_clusters: Number of sub-clusters per top-level cluster (Tactical Layer).
        """
        self.layer2_k = layer2_clusters
        self.layer1_k = layer1_clusters
        
        self.layer2_centroids = None
        self.layer1_centroids = {} # Map: layer2_id -> {layer1_id: centroid}
        self.layer1_children = {}  # Map: layer2_id -> {layer1_id: [item_indices]}
        
        self.vectors = None
        self.ids = None
        self.payloads = None
        
        # Stats for verification
        self.stats = {
            "comparisons": 0
        }

    def build(self, vectors, ids, payloads=None):
        """
        Builds the 3-layer hierarchy:
        Layer 2: Global Centroids
        Layer 1: Local Centroids within each Layer 2 cluster
        Layer 0: Actual Data Points
        """
        print("🏗️ Building Hierarchical Index...")
        self.vectors = np.array(vectors).astype('float32')
        self.ids = np.array(ids)
        self.payloads = payloads if payloads else [{}] * len(ids)
        
        # --- Layer 2 Construction ---
        print(f"   - Clustering Layer 2 ({self.layer2_k} centroids)...")
        kmeans_l2 = KMeans(n_clusters=self.layer2_k, n_init=10, random_state=42)
        l2_labels = kmeans_l2.fit_predict(self.vectors)
        self.layer2_centroids = kmeans_l2.cluster_centers_
        
        # --- Layer 1 Construction ---
        print(f"   - Clustering Layer 1 (Recursive)...")
        for l2_id in range(self.layer2_k):
            # Get all vectors belonging to this L2 cluster
            indices = np.where(l2_labels == l2_id)[0]
            if len(indices) == 0:
                continue
            
            sub_vectors = self.vectors[indices]
            
            # Dynamic K for Layer 1: If cluster is small, don't force k=10
            k = min(self.layer1_k, len(indices))
            if k < 1: k = 1
            
            kmeans_l1 = KMeans(n_clusters=k, n_init=10, random_state=42)
            l1_labels = kmeans_l1.fit_predict(sub_vectors)
            
            self.layer1_centroids[l2_id] = kmeans_l1.cluster_centers_
            
            # Map L1 centroids to actual item indices
            self.layer1_children[l2_id] = {}
            for local_l1_id in range(k):
                # indices[x] maps back to global index
                local_indices = np.where(l1_labels == local_l1_id)[0]
                global_indices = indices[local_indices]
                self.layer1_children[l2_id][local_l1_id] = global_indices
        
        print("✅ Hierarchy Built.")

    def search(self, query_vector, top_k=10, beam_size=3):
        """
        Coarse-to-Fine Search with Beam Search.
        Returns: List of dicts {'id': ..., 'score': ..., 'payload': ...}
        """
        self.stats["comparisons"] = 0
        query_vector = np.array(query_vector).reshape(1, -1)
        
        # --- Step 1: Layer 2 Search (Strategic) ---
        # Compare query against all L2 centroids
        # Sim: Dot product (assuming normalized) or L2 distance. Using Dot Product here.
        l2_scores = np.dot(self.layer2_centroids, query_vector.T).flatten()
        self.stats["comparisons"] += len(self.layer2_centroids)
        
        # Beam Search: Keep top 'beam_size' L2 clusters
        top_l2_indices = np.argsort(l2_scores)[::-1][:beam_size]
        
        # --- Step 2: Layer 1 Search (Tactical) ---
        candidates_l1 = [] # List of (l2_id, l1_id, score)
        
        for l2_id in top_l2_indices:
            if l2_id not in self.layer1_centroids:
                continue
                
            centroids = self.layer1_centroids[l2_id]
            l1_scores = np.dot(centroids, query_vector.T).flatten()
            self.stats["comparisons"] += len(centroids)
            
            # Keep top 'beam_size' L1 clusters from THIS L2 branch
            # (Or we could pool all L1 candidates and pick top K, but per-branch is safer for diversity)
            top_l1_local = np.argsort(l1_scores)[::-1][:beam_size]
            
            for l1_id in top_l1_local:
                candidates_l1.append((l2_id, l1_id))
        
        # --- Step 3: Layer 0 Search (Execution) ---
        final_candidates = []
        
        for l2_id, l1_id in candidates_l1:
            if l2_id in self.layer1_children and l1_id in self.layer1_children[l2_id]:
                item_indices = self.layer1_children[l2_id][l1_id]
                
                # Fetch vectors
                item_vectors = self.vectors[item_indices]
                scores = np.dot(item_vectors, query_vector.T).flatten()
                self.stats["comparisons"] += len(item_vectors)
                
                for idx, score in zip(item_indices, scores):
                    final_candidates.append({
                        "id": self.ids[idx],
                        "score": float(score),
                        "payload": self.payloads[idx]
                    })
        
        # Final Sort
        final_candidates.sort(key=lambda x: x['score'], reverse=True)
        return final_candidates[:top_k]

    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self, f)
            
    @staticmethod
    def load(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
