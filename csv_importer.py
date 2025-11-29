"""
CSV导入模块 - 用于批量导入Wiki类型的数据
支持从CSV文件批量导入数据到数据库，避免重复爬取
"""
import csv
import io
import uuid
from typing import List, Dict, Optional, Callable
from qdrant_client.http import models
from system_manager import SystemManager, SPACE_X, SPACE_R
import asyncio

class CSVImporter:
    """CSV数据导入器"""
    
    def __init__(self, system_manager: SystemManager):
        self.mgr = system_manager
        self.client = system_manager.client
        
    def parse_csv(self, csv_content: str, encoding: str = 'utf-8') -> List[Dict[str, str]]:
        """
        解析CSV内容
        
        Args:
            csv_content: CSV文件内容（字符串）
            encoding: 编码格式，默认utf-8
            
        Returns:
            List[Dict]: 解析后的数据行列表
        """
        try:
            # 尝试使用指定编码
            if isinstance(csv_content, bytes):
                csv_content = csv_content.decode(encoding)
        except UnicodeDecodeError:
            # 如果失败，尝试其他编码
            try:
                csv_content = csv_content.decode('latin-1')
            except:
                csv_content = csv_content.decode('utf-8', errors='ignore')
        
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = []
        
        for row in reader:
            # 清理空值
            cleaned_row = {k: v.strip() if v else '' for k, v in row.items()}
            rows.append(cleaned_row)
        
        return rows
    
    def prepare_row_data(self, row: Dict[str, str], default_url_prefix: str = "") -> Optional[Dict]:
        """
        准备单行数据用于导入
        
        支持的CSV列名（不区分大小写）：
        - title: 标题
        - content / text / body: 内容
        - url / link: URL链接
        - category / type: 分类
        
        Args:
            row: CSV行数据字典
            default_url_prefix: 默认URL前缀（如果CSV中没有URL，自动生成）
            
        Returns:
            Dict: 准备好的数据，包含text和url，如果数据无效则返回None
        """
        # 不区分大小写的字段查找
        row_lower = {k.lower(): v for k, v in row.items()}
        
        # 查找内容字段（优先级：content > text > body）
        text = None
        for field in ['content', 'text', 'body', 'description', 'abstract']:
            if field in row_lower and row_lower[field]:
                text = row_lower[field]
                break
        
        # 如果还没有找到，尝试使用所有字段组合
        if not text:
            # 组合除了URL和标题外的所有字段
            text_parts = []
            for key, value in row.items():
                key_lower = key.lower()
                if key_lower not in ['url', 'link', 'title', 'category', 'type'] and value:
                    text_parts.append(f"{key}: {value}")
            text = ' '.join(text_parts) if text_parts else None
        
        if not text or len(text.strip()) < 10:  # 内容太短，跳过
            return None
        
        # 查找URL字段
        url = None
        for field in ['url', 'link', 'href']:
            if field in row_lower and row_lower[field]:
                url = row_lower[field]
                break
        
        # 如果没有URL，尝试从标题生成
        if not url:
            title = None
            for field in ['title', 'name', 'page']:
                if field in row_lower and row_lower[field]:
                    title = row_lower[field]
                    break
            
            if title and default_url_prefix:
                # 生成基于标题的URL
                url = f"{default_url_prefix}/{title.replace(' ', '_')}"
            elif title:
                url = f"csv_import/{title.replace(' ', '_')}"
            else:
                url = f"csv_import/{uuid.uuid4().hex[:8]}"
        
        # 组合标题和内容
        title = None
        for field in ['title', 'name', 'page']:
            if field in row_lower and row_lower[field]:
                title = row_lower[field]
                break
        
        if title:
            full_text = f"{title}\n\n{text}"
        else:
            full_text = text
        
        return {
            'text': full_text,
            'url': url,
            'title': title or '',
            'category': row_lower.get('category', '') or row_lower.get('type', '')
        }
    
    def import_csv_batch(
        self, 
        csv_rows: List[Dict[str, str]], 
        batch_size: int = 50,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        default_url_prefix: str = "",
        promote_novel: bool = True,
        check_db_first: bool = True
    ) -> Dict[str, int]:
        """
        批量导入CSV数据到数据库
        
        Args:
            csv_rows: CSV行数据列表
            batch_size: 批处理大小
            progress_callback: 进度回调函数 callback(current, total, message)
            default_url_prefix: 默认URL前缀
            promote_novel: 是否自动提升独特内容到Space R
            
        Returns:
            Dict: 导入统计信息
        """
        stats = {
            'total': len(csv_rows),
            'processed': 0,
            'success': 0,
            'failed': 0,
            'promoted': 0,
            'skipped': 0  # 数据库已存在而跳过的数量
        }
        
        batch_points_x = []
        batch_points_r = []
        
        for idx, row in enumerate(csv_rows):
            try:
                # 准备数据
                row_data = self.prepare_row_data(row, default_url_prefix)
                if not row_data:
                    stats['failed'] += 1
                    continue
                
                text = row_data['text']
                url = row_data['url']
                
                # 检查数据库（如果启用）
                if check_db_first:
                    if self.mgr.check_url_exists(url, SPACE_X):
                        stats['skipped'] = stats.get('skipped', 0) + 1
                        stats['processed'] += 1
                        if progress_callback:
                            progress_callback(
                                stats['processed'], 
                                stats['total'], 
                                f"跳过（已存在）: {url[:50]}..."
                            )
                        continue
                
                # 生成向量
                try:
                    vec = self.mgr.get_text_embedding(text)
                    if not vec:
                        stats['failed'] += 1
                        continue
                except Exception as e:
                    print(f"   ❌ Error generating embedding for row {idx}: {e}")
                    stats['failed'] += 1
                    continue
                
                # 构造payload
                payload = {
                    "url": url,
                    "type": "text",
                    "content": text,
                    "full_text": text,
                    "content_preview": text[:100],
                    "pr_score": 0.0,
                    "is_summarized": False,
                    "source": "csv_import"
                }
                
                # 添加标题和分类（如果有）
                if row_data.get('title'):
                    payload['title'] = row_data['title']
                if row_data.get('category'):
                    payload['category'] = row_data['category']
                
                pt_id = str(uuid.uuid4())
                
                # 检查是否需要晋升到R空间（独特性检测）
                should_promote = False
                if promote_novel:
                    try:
                        is_novel, dist = self.mgr._check_novelty(vec)
                        if is_novel:
                            should_promote = True
                            stats['promoted'] += 1
                    except Exception as e:
                        print(f"   ⚠️ Novelty check failed: {e}, skipping promotion")
                
                # 添加到Space X
                batch_points_x.append(
                    models.PointStruct(
                        id=pt_id,
                        vector={"clip": vec},
                        payload=payload
                    )
                )
                
                # 如果需要晋升，添加到Space R
                if should_promote:
                    batch_points_r.append(
                        models.PointStruct(
                            id=pt_id,
                            vector={"clip": vec},
                            payload=payload
                        )
                    )
                
                # 批量插入
                if len(batch_points_x) >= batch_size:
                    self._flush_batches(batch_points_x, batch_points_r)
                    batch_points_x.clear()
                    batch_points_r.clear()
                
                stats['success'] += 1
                stats['processed'] += 1
                
                # 进度回调
                if progress_callback:
                    progress_callback(
                        stats['processed'], 
                        stats['total'], 
                        f"处理中: {url[:50]}..."
                    )
                    
            except Exception as e:
                print(f"❌ Error processing row {idx}: {e}")
                stats['failed'] += 1
                continue
        
        # 处理剩余的批次
        if batch_points_x:
            self._flush_batches(batch_points_x, batch_points_r)
        
        return stats
    
    def _flush_batches(self, batch_x: List, batch_r: List):
        """批量插入数据到数据库"""
        if batch_x:
            self.client.upsert(
                collection_name=SPACE_X,
                points=batch_x
            )
        
        if batch_r:
            self.client.upsert(
                collection_name=SPACE_R,
                points=batch_r
            )
    
    def import_csv_file(
        self,
        file_path: str,
        batch_size: int = 50,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        default_url_prefix: str = "",
        promote_novel: bool = True,
        encoding: str = 'utf-8'
    ) -> Dict[str, int]:
        """
        从CSV文件导入数据
        
        Args:
            file_path: CSV文件路径
            batch_size: 批处理大小
            progress_callback: 进度回调
            default_url_prefix: 默认URL前缀
            promote_novel: 是否自动提升独特内容
            encoding: 文件编码
            
        Returns:
            Dict: 导入统计信息
        """
        # 读取文件
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                csv_content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(file_path, 'r', encoding='latin-1') as f:
                csv_content = f.read()
        
        # 解析CSV
        rows = self.parse_csv(csv_content, encoding)
        
        if not rows:
            return {'total': 0, 'processed': 0, 'success': 0, 'failed': 0, 'promoted': 0}
        
        # 批量导入
        return self.import_csv_batch(
            rows,
            batch_size=batch_size,
            progress_callback=progress_callback,
            default_url_prefix=default_url_prefix,
            promote_novel=promote_novel
        )
