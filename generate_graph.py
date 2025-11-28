import json
import random
import csv
import os

# 路径设置：确保读取和保存都在 mock_data 文件夹下
# 获取当前脚本所在的目录
base_path = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(base_path, 'mock_data', 'tum_content.json')
csv_path = os.path.join(base_path, 'mock_data', 'edges.csv')


def generate_edges():
    # 1. 读取内容数据
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {json_path}。请确保你先完成了第2步创建了json文件。")
        return

    ids = [item['id'] for item in data]
    # 模拟跳转连线的数量：大概是节点数的 2-3 倍，让图稍微稠密一点
    num_edges = len(ids) * 3

    edges = []

    print(f"正在为 {len(ids)} 个内容节点生成模拟跳转关系...")

    # 2. 模拟逻辑
    for _ in range(num_edges):
        src = random.choice(ids)
        dst = random.choice(ids)

        # 规则1：不自己跳自己
        if src == dst:
            continue

        # 规则2：获取详细对象，模拟真实逻辑
        src_obj = next(item for item in data if item['id'] == src)
        dst_obj = next(item for item in data if item['id'] == dst)

        # 逻辑模拟：如果是同一个URL（同一个网页），从 Text 跳转到 Image 的概率极高
        if src_obj['url'] == dst_obj['url'] and src_obj['type'] != dst_obj['type']:
            # 这是一个强关联，必须保留
            edges.append((src, dst))
        else:
            # 这里的随机是为了模拟“相关推荐”跳转
            edges.append((src, dst))

    # 去重
    edges = list(set(edges))

    # 3. 写入 CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['source_id', 'target_id'])  # 表头
        writer.writerows(edges)

    print(f"成功！已生成 {len(edges)} 条跳转关系，保存在: {csv_path}")
    print("准备进入下一步：将数据上传至 Colab 进行向量化。")


if __name__ == "__main__":
    generate_edges()