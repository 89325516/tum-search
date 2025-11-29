#!/usr/bin/env python3
"""
边（链接关系）导入工具
从CSV文件导入Wiki页面之间的链接关系到InteractionManager
"""
import csv
import sys
from collections import defaultdict
from system_manager import SystemManager, SPACE_X
from interaction_manager import InteractionManager


def import_edges_from_csv(edges_csv_path: str, system_manager: SystemManager, base_url: str = ""):
    """
    从边的CSV文件导入链接关系到InteractionManager
    
    CSV格式：
    source_title, target_title
    
    注意：这里使用title，需要先映射到数据库中的item_id（通过URL或title）
    """
    print(f"📂 读取边CSV文件: {edges_csv_path}")
    
    # 读取所有边的映射关系
    edges = []
    try:
        with open(edges_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                source_title = row.get('source_title', '').strip()
                target_title = row.get('target_title', '').strip()
                if source_title and target_title:
                    edges.append((source_title, target_title))
    except Exception as e:
        print(f"❌ 读取CSV文件失败: {e}")
        return
    
    print(f"   读取到 {len(edges)} 条边")
    
    # 构建标题/URL到数据库ID的映射
    print("🔍 构建标题到ID的映射...")
    title_to_id = {}
    url_to_id = {}
    
    # 辅助函数：标题转URL路径
    def title_to_url_path(title):
        return title.replace(' ', '_')
    
    # 从数据库中查询所有页面，建立映射
    offset = None
    page_count = 0
    while True:
        batch, offset = system_manager.client.scroll(
            collection_name=SPACE_X,
            limit=100,
            with_payload=True,
            offset=offset
        )
        
        for point in batch:
            payload = point.payload
            url = payload.get('url', '')
            title = payload.get('title', '')
            
            # 存储URL到ID的映射
            if url:
                url_to_id[url] = point.id
                # 也尝试从URL提取标题进行映射
                url_parts = url.split('/')
                if url_parts:
                    url_title = url_parts[-1].replace('_', ' ')
                    if url_title:
                        title_to_id[url_title] = point.id
            
            # 存储title到ID的映射
            if title:
                title_to_id[title] = point.id
                # 也尝试构建可能的URL进行映射
                if base_url:
                    possible_url = f"{base_url}/{title_to_url_path(title)}"
                    url_to_id[possible_url] = point.id
        
        page_count += len(batch)
        if page_count % 1000 == 0:
            print(f"   已处理 {page_count} 个页面...")
        
        if offset is None:
            break
    
    print(f"   ✅ 找到 {len(title_to_id)} 个标题映射, {len(url_to_id)} 个URL映射")
    
    # 导入边到InteractionManager
    print("📦 导入边到InteractionManager...")
    
    imported_count = 0
    skipped_count = 0
    
    for source_title, target_title in edges:
        # 尝试通过标题查找ID
        source_id = title_to_id.get(source_title)
        target_id = title_to_id.get(target_title)
        
        # 如果找不到，尝试通过URL查找
        if not source_id and base_url:
            source_url = f"{base_url}/{title_to_url_path(source_title)}"
            source_id = url_to_id.get(source_url)
        
        if not target_id and base_url:
            target_url = f"{base_url}/{title_to_url_path(target_title)}"
            target_id = url_to_id.get(target_url)
        
        if not source_id or not target_id:
            skipped_count += 1
            if skipped_count <= 10:  # 只显示前10个失败的
                print(f"   ⚠️  跳过: {source_title} -> {target_title} (找不到ID映射)")
            continue
        
        # 记录transition（链接关系）
        # 使用record_interaction来记录，这会自动保存到transitions
        system_manager.interaction_mgr.record_interaction(
            item_id=target_id,
            action_type="click",
            source_id=source_id
        )
        
        imported_count += 1
        
        # 每100条保存一次
        if imported_count % 100 == 0:
            system_manager.interaction_mgr.save()
            print(f"   已导入 {imported_count} 条边...")
    
    # 最终保存
    system_manager.interaction_mgr.save()
    
    print(f"✅ 边导入完成!")
    print(f"   成功导入: {imported_count}")
    print(f"   跳过（找不到映射）: {skipped_count}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='从CSV文件导入Wiki页面链接关系到数据库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python import_edges.py wiki_edges.csv --base-url "https://wiki.example.com"
  
CSV格式:
  source_title,target_title
  "Machine Learning","Deep Learning"
  "Python Programming","Data Science"
        """
    )
    
    parser.add_argument('edges_csv', help='边CSV文件路径（格式: source_title,target_title）')
    parser.add_argument('--base-url', default='', 
                       help='Wiki基础URL（用于构建URL映射）')
    
    args = parser.parse_args()
    
    print("🚀 初始化系统管理器...")
    try:
        mgr = SystemManager()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)
    
    # 导入边
    try:
        import_edges_from_csv(args.edges_csv, mgr, base_url=args.base_url)
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
