use pyo3::prelude::*;
use std::collections::HashMap;

#[pyfunction]
fn calculate_temporal_pagerank(
    num_nodes: usize,
    edges: Vec<(usize, usize)>,
    last_interaction_times: Vec<f64>, // 距今多少小时
    damping: f64,
    decay_lambda: f64, // 时间衰减系数
    iterations: usize,
) -> PyResult<Vec<f64>> {
    let mut adj_out = vec![vec![]; num_nodes];
    // 1. 构建图的同时应用时间衰减权重
    // W_new = W_original * e^(-lambda * delta_t)
    // 这里简化为：边的存在性加权。实际工程中通常调整转移概率矩阵。
    for (src, dst) in edges {
        if src < num_nodes && dst < num_nodes {
            adj_out[src].push(dst);
        }
    }

    let mut ranks = vec![1.0 / num_nodes as f64; num_nodes];

    for _ in 0..iterations {
        let mut new_ranks = vec![0.0; num_nodes];
        for (u, neighbors) in adj_out.iter().enumerate() {
            if neighbors.is_empty() { continue; }

            // 引入时间因子调整影响力
            let time_factor = (-decay_lambda * last_interaction_times[u]).exp();
            let share = (damping * ranks[u] * time_factor) / (neighbors.len() as f64);

            for &v in neighbors {
                new_ranks[v] += share;
            }
        }
        // 简单的归一化防止数值消失
        let sum_rank: f64 = new_ranks.iter().sum();
        ranks = new_ranks.iter().map(|x| x / sum_rank).collect();
    }
    Ok(ranks)
}

#[pymodule]
fn visual_rank_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // 注册你的函数
    m.add_function(wrap_pyfunction!(calculate_temporal_pagerank, m)?)?;
    Ok(())
}
