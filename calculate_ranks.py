import pandas as pd
import json
import visual_rank_engine  # 调用你写的 Rust 库
import os

def run_pagerank():
    # 1. 读取数据
    try:
        edges_df = pd.read_csv('mock_data/edges.csv')
        with open('mock_data/tum_content.json', 'r') as f:
            content_data = json.load(f)
    except FileNotFoundError:
        print("❌ Data file not found, please check mock_data folder")
        return

    # 2. 准备图数据 (Source -> Target)
    # Rust 引擎需要 [(src, dst)] 格式的列表
    edges = list(zip(edges_df['source_id'], edges_df['target_id']))

    # 获取总节点数 (假设 ID 是连续的，取最大ID + 1)
    max_id = max([x['id'] for x in content_data])
    num_nodes = max_id + 1

    # 3. 模拟“最后交互时间” (用于时间衰减 [cite: 63])
    # 我们从 json 里提取 timestamp_hours_ago
    # 创建一个列表，索引是 ID，值是 hours_ago
    last_interactions = [0.0] * num_nodes
    for item in content_data:
        last_interactions[item['id']] = item.get('timestamp_hours_ago', 24.0)

    print(f"🚀 Calling Rust Engine to calculate Temporal PageRank for {num_nodes} nodes...")

    # 4. 调用 Rust 函数 [cite: 128]
    # 参数: num_nodes, edges, timestamps, damping(阻尼系数), decay(衰减系数), iterations
    scores = visual_rank_engine.calculate_temporal_pagerank(
        num_nodes,
        edges,
        last_interactions,
        0.85,  # Damping factor
        0.01,  # Time decay lambda
        50     # Iterations
    )

    # 5. 保存结果
    # 我们把分数存成字典: {id: score}
    rank_dict = {i: score for i, score in enumerate(scores) if score > 0}

    with open('mock_data/pagerank_scores.json', 'w') as f:
        json.dump(rank_dict, f)

    print(f"✅ Calculation complete! Scores saved to mock_data/pagerank_scores.json")
    # 打印前5名看看
    top_5 = sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    print("🏆 Top 5 Authoritative Page IDs:", top_5)

if __name__ == "__main__":
    run_pagerank()