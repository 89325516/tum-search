use pyo3::prelude::*;
use std::collections::HashMap;
use hnsw_rs::prelude::*;
use rayon::prelude::*; // Import Rayon for parallelism

/// Calculate PageRank using HNSW for graph construction
///
/// Returns a HashMap mapping Point IDs to their calculated Rank.
#[pyfunction]
fn calculate_hnsw_pagerank(
    ids: Vec<String>,
    vectors: Vec<Vec<f32>>,
    interaction_weights: HashMap<String, f64>,
    transitions: HashMap<String, HashMap<String, usize>>,
    m_neighbors: usize,
    damping: f64,
    iterations: usize,
) -> PyResult<HashMap<String, f64>> {
    let n = ids.len();
    if n == 0 {
        return Ok(HashMap::new());
    }

    // --- Phase 1: Build HNSW Index (Construction) ---
    // HNSW construction can be costly, but hnsw_rs is efficient.
    let hnsw = Hnsw::new(
        m_neighbors, 
        n, 
        16,     // max_layer
        200,    // ef_construction
        DistCosine
    );

    // Parallel insertion is tricky with standard hnsw_rs without locking, 
    // keeping sequential insertion for safety.
    let data_with_ids: Vec<(&Vec<f32>, usize)> = vectors.iter().enumerate().map(|(i, v)| (v, i)).collect();
    for (vec, i) in data_with_ids {
        hnsw.insert((vec, i));
    }

    // --- Phase 2: Build Graph / Adjacency Matrix (Parallelized) ---
    // We use Rayon (par_iter) here because searching is read-only and thread-safe.
    // This transforms the O(N * log N) search into O(N * log N / Cores).
    
    // Pre-process weights to Vector for O(1) access and cache friendliness
    // This also avoids HashMap lookup contention if any (though HashMap is Sync)
    // let weight_vec: Vec<f64> = ids.iter()
    //    .map(|id| *interaction_weights.get(id).unwrap_or(&1.0))
    //    .collect();

    // We need to access transitions map in parallel. 
    // Since HashMap is Sync (for String keys/values), we can share it across threads.
    // However, looking up strings by reference in the hot loop might be slow.
    // For this implementation, we'll stick to the safe parallel logic.
    
    let adj_out: Vec<Vec<(usize, f64)>> = (0..n).into_par_iter().map(|i| {
        let query_vec = &vectors[i];
        let neighbors = hnsw.search(query_vec, m_neighbors, 2 * m_neighbors);
        
        let mut edges = Vec::with_capacity(neighbors.len());
        
        for neighbor in neighbors {
            let j = neighbor.d_id;
            if i == j { continue; } // Skip self-loops in construction

            // 1. Semantic Similarity
            let dist = neighbor.distance;
            let semantic_sim = (1.0_f32 - dist).max(0.0_f32) as f64;

            // 2. Interaction Weight (Target Popularity)
            let target_id = &ids[j];
            let target_weight = *interaction_weights.get(target_id).unwrap_or(&1.0);
            // We need to look up transitions[ids[i]][ids[j]]
            let source_id = &ids[i];
            let target_id = &ids[j];
            
            let transition_boost = if let Some(targets) = transitions.get(source_id) {
                if let Some(count) = targets.get(target_id) {
                    1.0 + (0.5 * (*count as f64))
                } else { 1.0 }
            } else { 1.0 };

            // Formula
            let final_weight = semantic_sim * target_weight * transition_boost;
            edges.push((j, final_weight));
        }
        edges
    }).collect();

    // --- Phase 3: Power Iteration (Optimized) ---
    let mut ranks = vec![1.0 / n as f64; n];
    let base_teleport = (1.0 - damping) / n as f64;

    for _ in 0..iterations {
        let mut new_ranks = vec![base_teleport; n];
        let mut dangling_rank_sum = 0.0;

        // 1. Distribute Flow
        for i in 0..n {
            let out_edges = &adj_out[i];
            
            if out_edges.is_empty() {
                // Collect energy from dangling nodes (Dead Ends)
                dangling_rank_sum += ranks[i];
            } else {
                let total_weight: f64 = out_edges.iter().map(|(_, w)| w).sum();
                
                if total_weight == 0.0 {
                     // Treat as dangling if total weight is 0 (e.g. all neighbors have 0 similarity)
                     dangling_rank_sum += ranks[i];
                     continue;
                }

                for &(j, w) in out_edges {
                    // Distribute proportional to edge weight
                    let share = (ranks[i] * w) / total_weight;
                    new_ranks[j] += damping * share;
                }
            }
        }

        // 2. Distribute Dangling Energy
        // The energy from dead ends is re-distributed to everyone (random jump)
        if dangling_rank_sum > 0.0 {
            let dangling_share = (damping * dangling_rank_sum) / n as f64;
            for r in new_ranks.iter_mut() {
                *r += dangling_share;
            }
        }

        ranks = new_ranks;
    }

    // --- Phase 4: Output ---
    // Optional: Normalize result to sum to 1.0
    let sum_rank: f64 = ranks.iter().sum();
    let mut result = HashMap::new();
    for (i, r) in ranks.iter().enumerate() {
        result.insert(ids[i].clone(), r / sum_rank);
    }

    Ok(result)
}

#[pymodule]
fn visual_rank_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_hnsw_pagerank, m)?)?;
    Ok(())
}
