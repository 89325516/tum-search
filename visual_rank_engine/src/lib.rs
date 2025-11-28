use pyo3::prelude::*;
use std::collections::HashMap;
use hnsw_rs::prelude::*;

/// Calculate PageRank using HNSW for graph construction
///
/// # Arguments
/// * `ids` - List of point IDs
/// * `vectors` - List of vectors (each vector is a list of floats)
/// * `interaction_weights` - Map of ID -> Weight
/// * `transitions` - Map of Source ID -> Target ID -> Count
/// * `m_neighbors` - Number of neighbors for HNSW
/// * `damping` - PageRank damping factor
/// * `iterations` - Number of PageRank iterations
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

    // 1. Build HNSW Index
    // We use a simple Euclidean distance here since vectors are likely normalized (Cosine ~ Euclidean)
    // or we can use Cosine. Let's use Cosine for correctness with CLIP.
    let hnsw = Hnsw::new(
        m_neighbors, 
        n, 
        16, // max_layer
        200, // ef_construction
        DistCosine
    );

    // Insert data
    for (i, vec) in vectors.iter().enumerate() {
        hnsw.insert((vec, i));
    }

    // 2. Build Adjacency Matrix (Sparse)
    // adj[i] = [(target_idx, weight), ...]
    let mut adj_out: Vec<Vec<(usize, f64)>> = vec![vec![]; n];

    for i in 0..n {
        let query_vec = &vectors[i];
        // Query Top M neighbors
        // ef_search should be >= m_neighbors
        let neighbors = hnsw.search(query_vec, m_neighbors, 2 * m_neighbors);
        
        for neighbor in neighbors {
            let j = neighbor.d_id; // neighbor index
            if i == j { continue; }

            // Calculate Weight
            // 1. Semantic Similarity (1 - distance for Cosine in hnsw_rs usually, 
            // but hnsw_rs Cosine returns 1 - cos_sim. Wait, let's check.
            // hnsw_rs::dist::Cosine: returns 1.0 - dot_product (assuming normalized).
            // So similarity = 1.0 - distance.
            let dist = neighbor.distance;
            let semantic_sim = (1.0_f32 - dist).max(0.0_f32);

            // 2. Interaction Weight (Target Popularity)
            let target_id = &ids[j];
            let target_weight = *interaction_weights.get(target_id).unwrap_or(&1.0);

            // 3. Transition Boost
            let source_id = &ids[i];
            let transition_boost = if let Some(targets) = transitions.get(source_id) {
                if let Some(count) = targets.get(target_id) {
                    1.0 + (0.5 * (*count as f64))
                } else {
                    1.0
                }
            } else {
                1.0
            };

            let final_weight = semantic_sim as f64 * target_weight * transition_boost;
            adj_out[i].push((j, final_weight));
        }
    }

    // 3. PageRank Power Iteration
    let mut ranks = vec![1.0 / n as f64; n];
    
    for _ in 0..iterations {
        let mut new_ranks = vec![0.0; n];
        
        for i in 0..n {
            let out_edges = &adj_out[i];
            if out_edges.is_empty() {
                // Dangling node: distribute rank evenly (or to self, but evenly is standard)
                // For simplicity in this custom implementation, we might just ignore or distribute to all.
                // Let's distribute to all (random surfer jump)
                let share = ranks[i] / n as f64;
                for k in 0..n {
                    new_ranks[k] += share; // This is O(N^2) effectively if many dangling nodes!
                    // Optimization: Accumulate dangling sum and add later.
                }
                continue; 
            }

            let total_weight: f64 = out_edges.iter().map(|(_, w)| w).sum();
            
            if total_weight > 0.0 {
                for &(j, w) in out_edges {
                    let share = (ranks[i] * w) / total_weight;
                    // Damping applied here or at the end? Standard: (1-d)/N + d * sum(share)
                    new_ranks[j] += share;
                }
            }
        }

        // Apply damping and handle dangling sum optimization if we did that
        // Here we just do the standard formula transformation
        let mut next_ranks = vec![0.0; n];
        let base_score = (1.0 - damping) / n as f64;
        
        for i in 0..n {
            next_ranks[i] = base_score + damping * new_ranks[i];
        }
        ranks = next_ranks;
    }

    // 4. Normalize (Optional but good for stability)
    let sum_rank: f64 = ranks.iter().sum();
    if sum_rank > 0.0 {
        for r in ranks.iter_mut() {
            *r /= sum_rank;
        }
    }

    // 5. Map back to IDs
    let mut result = HashMap::new();
    for (i, rank) in ranks.iter().enumerate() {
        result.insert(ids[i].clone(), *rank);
    }

    Ok(result)
}

#[pymodule]
fn visual_rank_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_hnsw_pagerank, m)?)?;
    Ok(())
}
