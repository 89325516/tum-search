#!/usr/bin/env python3
"""
MediaWiki XML Dump 处理工具
解析MediaWiki XML dump文件，提取页面和链接关系，生成节点和边的CSV数据
支持一键导入到数据库
"""
import os
import sys
import csv
import argparse
import re
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from pathlib import Path

try:
    import mwxml
    import mwparserfromhell
except ImportError:
    print("❌ 缺少必需的依赖库。请运行: pip install mwxml mwparserfromhell")
    sys.exit(1)

# 导入系统管理器用于数据库导入
try:
    from system_manager import SystemManager, SPACE_X, SPACE_R
    from csv_importer import CSVImporter
    DB_AVAILABLE = True
except ImportError:
    print("⚠️  数据库导入功能不可用，将只生成CSV文件")
    DB_AVAILABLE = False


class MediaWikiDumpProcessor:
    """MediaWiki XML Dump处理器 - 支持MediaWiki、Wikipedia等多种Wiki格式"""
    
    def __init__(self, base_url: str = "", namespace_filter: Set[int] = None, wiki_type: str = "auto"):
        """
        初始化处理器
        
        Args:
            base_url: Wiki的基础URL，用于生成完整URL（例如: https://wiki.example.com）
            namespace_filter: 要处理的命名空间ID集合（None表示所有，通常0是主命名空间）
            wiki_type: Wiki类型 ("auto", "mediawiki", "wikipedia", "wikidata")
                      auto: 自动检测（基于dump文件中的站点信息）
        """
        self.base_url = base_url.rstrip('/')
        self.namespace_filter = namespace_filter or {0}  # 默认只处理主命名空间（0）
        self.wiki_type = wiki_type
        
        # Wiki类型特定配置
        self.wiki_configs = {
            "wikipedia": {
                "url_pattern": "{base_url}/wiki/{title}",
                "skip_namespaces": {'File', 'Image', 'Category', 'Template', 'Media', 'User', 'Talk', 'Help', 'Portal'},
                "link_patterns": [r'\[\[([^\]]+)\]\]']
            },
            "mediawiki": {
                "url_pattern": "{base_url}/{title}",
                "skip_namespaces": {'File', 'Image', 'Category', 'Template', 'Media'},
                "link_patterns": [r'\[\[([^\]]+)\]\]']
            },
            "wikidata": {
                "url_pattern": "{base_url}/wiki/{title}",
                "skip_namespaces": {'Property', 'Property talk', 'Item', 'Item talk'},
                "link_patterns": [r'\[\[([^\]]+)\]\]', r'Q\d+', r'P\d+']
            }
        }
        
        self.config = None  # 将在处理时自动检测或设置
        
        # 存储页面数据：page_title -> page_data
        self.pages: Dict[str, Dict] = {}
        
        # 存储链接关系：source_title -> [target_title1, target_title2, ...]
        self.links: Dict[str, List[str]] = defaultdict(list)
        
        # 标题到URL的映射
        self.title_to_url: Dict[str, str] = {}
        
        # 统计数据
        self.stats = {
            'total_pages': 0,
            'processed_pages': 0,
            'skipped_pages': 0,
            'total_links': 0,
            'unique_links': 0
        }
    
    def normalize_title(self, title: str) -> str:
        """规范化页面标题"""
        # MediaWiki标题规范：首字母大写，空格保留
        if not title:
            return ""
        # 移除命名空间前缀（如果有）
        parts = title.split(':', 1)
        if len(parts) > 1 and parts[0].lower() in ['file', 'image', 'category', 'template']:
            # 跳过文件、图像、分类、模板等特殊页面
            return None
        return title.replace('_', ' ')
    
    def title_to_url_path(self, title: str) -> str:
        """将标题转换为URL路径"""
        # MediaWiki URL格式：空格替换为下划线
        return title.replace(' ', '_')
    
    def _generate_url(self, title: str) -> str:
        """
        根据Wiki类型生成URL
        
        Args:
            title: 页面标题
            
        Returns:
            str: 完整的URL
        """
        if not self.base_url:
            return self.title_to_url_path(title)
        
        title_path = self.title_to_url_path(title)
        
        # 根据配置生成URL
        if self.config and 'url_pattern' in self.config:
            url_pattern = self.config['url_pattern']
            return url_pattern.format(base_url=self.base_url, title=title_path)
        
        # 默认格式（MediaWiki）
        return f"{self.base_url}/{title_path}"
    
    def extract_links_from_wikicode(self, wikitext: str) -> List[str]:
        """
        从MediaWiki wikicode中提取内部链接
        
        MediaWiki链接格式：
        - [[Page Title]]
        - [[Page Title|Display Text]]
        - [[Namespace:Page Title]]
        """
        if not wikitext:
            return []
        
        links = []
        
        try:
            # 使用mwparserfromhell解析wikicode
            wikicode = mwparserfromhell.parse(wikitext)
            
            # 提取所有内部链接
            for link in wikicode.filter_wikilinks():
                target = str(link.title).strip()
                
                # 跳过外部链接、文件链接等
                if ':' in target:
                    parts = target.split(':', 1)
                    namespace = parts[0].lower()
                    # 跳过特殊命名空间
                    if namespace in ['file', 'image', 'category', 'template', 'media']:
                        continue
                    # 如果是其他命名空间，可以保留或跳过
                    # 这里我们保留所有非特殊命名空间的链接
                
                # 规范化标题
                normalized = self.normalize_title(target)
                if normalized:
                    links.append(normalized)
        
        except Exception as e:
            # 如果解析失败，使用正则表达式作为后备
            print(f"   ⚠️  Wikicode解析失败，使用正则表达式提取: {e}")
            links = self._extract_links_regex(wikitext)
        
        return links
    
    def _extract_links_regex(self, wikitext: str) -> List[str]:
        """使用正则表达式提取链接（后备方案）"""
        links = []
        # MediaWiki链接格式：[[Page Title]] 或 [[Page Title|Display Text]]
        pattern = r'\[\[([^\]]+)\]\]'
        matches = re.findall(pattern, wikitext)
        
        for match in matches:
            # 处理带显示文本的链接：Page Title|Display Text
            target = match.split('|')[0].strip()
            
            # 跳过特殊命名空间
            if ':' in target:
                parts = target.split(':', 1)
                namespace = parts[0].lower()
                if namespace in ['file', 'image', 'category', 'template', 'media', 'http']:
                    continue
            
            normalized = self.normalize_title(target)
            if normalized:
                links.append(normalized)
        
        return links
    
    def process_dump(self, dump_path: str, max_pages: Optional[int] = None, 
                    progress_callback: Optional[callable] = None):
        """
        处理XML dump文件
        
        Args:
            dump_path: XML dump文件路径
            max_pages: 最大处理页面数（None表示处理所有）
            progress_callback: 进度回调函数 callback(current, total, message)
        """
        print(f"📂 开始处理XML dump: {dump_path}")
        
        if not os.path.exists(dump_path):
            raise FileNotFoundError(f"文件不存在: {dump_path}")
        
        # 根据文件扩展名选择正确的打开方式（支持压缩文件）
        dump_path_lower = dump_path.lower()
        if dump_path_lower.endswith('.bz2'):
            import bz2
            file_opener = lambda path: bz2.open(path, 'rt', encoding='utf-8')
            print("📦 检测到 bzip2 压缩文件")
        elif dump_path_lower.endswith('.gz'):
            import gzip
            file_opener = lambda path: gzip.open(path, 'rt', encoding='utf-8')
            print("📦 检测到 gzip 压缩文件")
        else:
            file_opener = lambda path: open(path, 'rb')
        
        # 打开dump文件
        with file_opener(dump_path) as f:
            dump = mwxml.Dump.from_file(f)
            
            # 显示站点信息并检测Wiki类型
            if dump.site_info:
                print(f"🌐 站点名称: {dump.site_info.name}")
                print(f"📦 数据库名: {dump.site_info.dbname}")
                
                # 自动检测Wiki类型
                if self.wiki_type == "auto":
                    site_name = dump.site_info.name.lower()
                    db_name = dump.site_info.dbname.lower()
                    
                    if "wikipedia" in site_name or "wikipedia" in db_name:
                        self.wiki_type = "wikipedia"
                        print(f"🔍 自动检测: Wikipedia格式")
                    elif "wikidata" in site_name or "wikidata" in db_name:
                        self.wiki_type = "wikidata"
                        print(f"🔍 自动检测: Wikidata格式")
                    else:
                        self.wiki_type = "mediawiki"
                        print(f"🔍 自动检测: MediaWiki格式")
                
                # 应用Wiki配置
                if self.wiki_type in self.wiki_configs:
                    self.config = self.wiki_configs[self.wiki_type]
                else:
                    self.config = self.wiki_configs["mediawiki"]  # 默认
            
            # 遍历所有页面
            page_count = 0
            for page in dump:
                page_count += 1
                
                # 检查命名空间
                if page.namespace not in self.namespace_filter:
                    continue
                
                # 限制处理数量
                if max_pages and self.stats['processed_pages'] >= max_pages:
                    break
                
                # 获取最新版本
                revisions = list(page)
                if not revisions:
                    self.stats['skipped_pages'] += 1
                    continue
                
                latest_revision = revisions[-1]
                page_text = latest_revision.text or ""
                
                # 规范化标题
                title = self.normalize_title(page.title)
                if not title:
                    self.stats['skipped_pages'] += 1
                    continue
                
                # 提取链接
                page_links = self.extract_links_from_wikicode(page_text)
                
                # 生成URL（根据Wiki类型使用不同格式）
                url = self._generate_url(title)
                
                self.pages[title] = {
                    'title': title,
                    'url': url,
                    'content': page_text,
                    'namespace': page.namespace,
                    'page_id': page.id,
                    'revision_id': latest_revision.id,
                    'timestamp': str(latest_revision.timestamp) if latest_revision.timestamp else None
                }
                
                # 填充 title_to_url 映射（用于边导入）
                self.title_to_url[title] = url
                
                # 存储链接关系
                if page_links:
                    self.links[title] = page_links
                    self.stats['total_links'] += len(page_links)
                
                self.stats['processed_pages'] += 1
                self.stats['total_pages'] = page_count
                
                # 进度回调
                if progress_callback and self.stats['processed_pages'] % 100 == 0:
                    progress_callback(
                        self.stats['processed_pages'],
                        self.stats['total_pages'],
                        f"已处理: {title[:50]}..."
                    )
        
        self.stats['unique_links'] = len(set(
            link for links in self.links.values() for link in links
        ))
        
        print(f"✅ 处理完成!")
        print(f"   总页面数: {self.stats['total_pages']}")
        print(f"   处理页面数: {self.stats['processed_pages']}")
        print(f"   跳过页面数: {self.stats['skipped_pages']}")
        print(f"   总链接数: {self.stats['total_links']}")
        print(f"   唯一链接目标数: {self.stats['unique_links']}")
    
    def generate_nodes_csv(self, output_path: str):
        """
        生成节点CSV文件（页面数据）
        
        CSV格式：
        title, content, url, category
        """
        print(f"📝 生成节点CSV: {output_path}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['title', 'content', 'url', 'category'])
            
            for title, page_data in self.pages.items():
                # 提取纯文本内容（去除wikicode标记）
                content = self._extract_text_from_wikicode(page_data['content'])
                
                # 只保留有内容的页面
                if len(content.strip()) < 50:
                    continue
                
                writer.writerow([
                    page_data['title'],
                    content,
                    page_data['url'],
                    'Wiki'  # 默认分类
                ])
        
        print(f"   ✅ 已生成 {len(self.pages)} 个节点")
    
    def generate_edges_csv(self, output_path: str):
        """
        生成边CSV文件（链接关系）
        
        CSV格式：
        source_title, target_title
        """
        print(f"🔗 生成边CSV: {output_path}")
        
        edges_written = 0
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['source_title', 'target_title'])
            
            for source_title, target_titles in self.links.items():
                for target_title in target_titles:
                    # 只写入目标页面也存在的链接（确保数据完整性）
                    if target_title in self.pages:
                        writer.writerow([source_title, target_title])
                        edges_written += 1
        
        print(f"   ✅ 已生成 {edges_written} 条边")
    
    def _extract_text_from_wikicode(self, wikitext: str) -> str:
        """
        从wikicode中提取纯文本内容
        """
        if not wikitext:
            return ""
        
        try:
            wikicode = mwparserfromhell.parse(wikitext)
            # 获取纯文本（移除所有wikicode标记）
            text = wikicode.strip_code()
            return text.strip()
        except Exception as e:
            # 如果解析失败，简单清理wikicode标记
            text = wikitext
            # 移除常见的wikicode标记
            text = re.sub(r'{{[^}]+}}', '', text)  # 模板
            text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)  # 链接
            text = re.sub(r'={2,}[^=]+={2,}', '', text)  # 标题
            text = re.sub(r"''+", '', text)  # 粗体/斜体
            return text.strip()
    
    def import_to_database(self, system_manager: SystemManager, 
                          url_prefix: str = "", batch_size: int = 50,
                          import_edges: bool = False, edges_csv_path: str = None,
                          check_db_first: bool = True):
        """
        一键导入到数据库
        
        Args:
            system_manager: SystemManager实例
            url_prefix: URL前缀（覆盖页面URL）
            batch_size: 批量大小
            import_edges: 是否同时导入边（链接关系）
            edges_csv_path: 边CSV文件路径（如果import_edges为True）
        """
        if not DB_AVAILABLE:
            print("❌ 数据库导入功能不可用")
            return
        
        print(f"📦 开始导入到数据库...")
        
        from csv_importer import CSVImporter
        importer = CSVImporter(system_manager)
        
        # 准备CSV格式的数据
        csv_rows = []
        for title, page_data in self.pages.items():
            content = self._extract_text_from_wikicode(page_data['content'])
            if len(content.strip()) < 50:
                continue
            
            url = page_data['url']
            if url_prefix:
                # 使用配置的URL模式或默认格式
                title_path = self.title_to_url_path(title)
                if self.config and 'url_pattern' in self.config:
                    url_pattern = self.config['url_pattern']
                    url = url_pattern.format(base_url=url_prefix, title=title_path)
                else:
                    url = f"{url_prefix}/{title_path}"
            
            csv_rows.append({
                'title': title,
                'content': content,
                'url': url,
                'category': 'Wiki'
            })
        
        # 导入数据
        stats = importer.import_csv_batch(
            csv_rows,
            batch_size=batch_size,
            default_url_prefix=url_prefix or self.base_url,
            promote_novel=True,
            check_db_first=check_db_first
        )
        
        print(f"✅ 数据库导入完成!")
        print(f"   总行数: {stats['total']}")
        print(f"   成功导入: {stats['success']}")
        print(f"   跳过（已存在）: {stats.get('skipped', 0)}")
        print(f"   失败: {stats['failed']}")
        print(f"   晋升到Space R: {stats['promoted']}")
        
        # 可选：导入边
        if import_edges:
            if edges_csv_path and os.path.exists(edges_csv_path):
                print(f"\n🔗 开始导入边...")
                try:
                    from import_edges import import_edges_from_csv
                    url_prefix_for_edges = url_prefix or self.base_url
                    import_edges_from_csv(edges_csv_path, system_manager, base_url=url_prefix_for_edges)
                except Exception as e:
                    print(f"⚠️  边导入失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("⚠️  未指定边CSV文件路径，跳过边导入")
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description='MediaWiki XML Dump处理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 只生成CSV文件
  python xml_dump_processor.py dump.xml --base-url "https://wiki.example.com"
  
  # 生成CSV并导入数据库
  python xml_dump_processor.py dump.xml --base-url "https://wiki.example.com" --import-db
  
  # 只处理前1000个页面（测试用）
  python xml_dump_processor.py dump.xml --max-pages 1000
        """
    )
    
    parser.add_argument('dump_file', help='MediaWiki XML dump文件路径')
    parser.add_argument('--base-url', default='', 
                       help='Wiki基础URL（例如: https://wiki.example.com）')
    parser.add_argument('--output-dir', default='.', 
                       help='输出目录（默认: 当前目录）')
    parser.add_argument('--nodes-csv', default='wiki_nodes.csv',
                       help='节点CSV文件名（默认: wiki_nodes.csv）')
    parser.add_argument('--edges-csv', default='wiki_edges.csv',
                       help='边CSV文件名（默认: wiki_edges.csv）')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='最大处理页面数（用于测试）')
    parser.add_argument('--import-db', action='store_true',
                       help='一键导入到数据库')
    parser.add_argument('--import-edges', action='store_true',
                       help='同时导入边（链接关系）到InteractionManager')
    parser.add_argument('--url-prefix', default='',
                       help='数据库导入时的URL前缀（覆盖base-url）')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='数据库批量导入大小（默认: 50）')
    parser.add_argument('--check-db', action='store_true', default=True,
                       help='导入前检查数据库，跳过已存在的URL（默认: True）')
    parser.add_argument('--no-check-db', dest='check_db', action='store_false',
                       help='禁用数据库检查，强制导入所有数据')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 初始化处理器（支持wiki-type参数，但目前先使用auto自动检测）
    processor = MediaWikiDumpProcessor(
        base_url=args.base_url,
        wiki_type="auto"  # 自动检测Wiki类型
    )
    
    # 处理dump文件
    try:
        processor.process_dump(args.dump_file, max_pages=args.max_pages)
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 生成CSV文件
    nodes_path = os.path.join(args.output_dir, args.nodes_csv)
    edges_path = os.path.join(args.output_dir, args.edges_csv)
    
    processor.generate_nodes_csv(nodes_path)
    processor.generate_edges_csv(edges_path)
    
    print(f"\n✅ CSV文件生成完成:")
    print(f"   节点文件: {nodes_path}")
    print(f"   边文件: {edges_path}")
    
    # 可选：导入数据库
    if args.import_db:
        if not DB_AVAILABLE:
            print("\n❌ 数据库导入功能不可用，请检查system_manager和csv_importer模块")
            sys.exit(1)
        
        print("\n📦 开始导入到数据库...")
        try:
            mgr = SystemManager()
            url_prefix = args.url_prefix or args.base_url
            edges_csv_path = edges_path if args.import_edges else None
            processor.import_to_database(
                mgr, 
                url_prefix=url_prefix, 
                batch_size=args.batch_size,
                import_edges=args.import_edges,
                edges_csv_path=edges_csv_path,
                check_db_first=args.check_db
            )
        except Exception as e:
            print(f"❌ 数据库导入失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
