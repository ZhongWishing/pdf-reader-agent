import os
import uuid
from typing import List, Dict, Any
from pdf2image import convert_from_path
from PIL import Image
import json
from datetime import datetime
from config import Config

class PDFProcessor:
    """PDF处理服务"""
    
    def __init__(self):
        self.upload_dir = Config.UPLOAD_FOLDER
        self.data_dir = Config.DATA_FOLDER
        self.images_dir = os.path.join(self.data_dir, 'images')
        
        # 确保目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
    
    def process_pdf(self, pdf_path: str, filename: str, progress_callback=None) -> Dict[str, Any]:
        """处理PDF文件
        
        Args:
            pdf_path: PDF文件路径
            filename: 原始文件名
            progress_callback: 进度回调函数
            
        Returns:
            处理结果信息
        """
        try:
            # 生成文档ID
            document_id = str(uuid.uuid4())
            
            if progress_callback:
                progress_callback(document_id, 10, "开始转换PDF为图片...")
            
            # 转换PDF为图片
            images = convert_from_path(
                pdf_path,
                dpi=200,  # 设置DPI以获得清晰图片
                fmt='PNG',
                thread_count=2
            )
            
            if progress_callback:
                progress_callback(document_id, 30, f"PDF转换完成，共{len(images)}页，开始保存图片...")
            
            # 保存图片并记录信息
            page_info = []
            doc_images_dir = os.path.join(self.images_dir, document_id)
            os.makedirs(doc_images_dir, exist_ok=True)
            
            total_pages = len(images)
            for i, image in enumerate(images):
                page_number = i + 1
                image_filename = f'page_{page_number}.png'
                image_path = os.path.join(doc_images_dir, image_filename)
                
                # 优化图片质量和大小
                optimized_image = self._optimize_image(image)
                optimized_image.save(image_path, 'PNG', optimize=True)
                
                page_info.append({
                    'page_number': page_number,
                    'image_path': image_path,
                    'image_filename': image_filename
                })
                
                # 更新进度
                if progress_callback:
                    progress = 30 + int((i + 1) / total_pages * 60)  # 30-90%
                    progress_callback(document_id, progress, f"正在保存第{page_number}/{total_pages}页...")
            
            if progress_callback:
                progress_callback(document_id, 95, "正在保存文档元数据...")
            
            # 获取文件信息
            file_size = os.path.getsize(pdf_path)
            
            # 创建文档元数据
            document_data = {
                'id': document_id,
                'filename': filename,
                'original_path': pdf_path,
                'file_size': file_size,
                'total_pages': len(images),
                'created_at': datetime.now().isoformat(),
                'status': 'processed',
                'pages': page_info,
                'summary': None,  # 将在后续生成
                'conversations': []  # 对话历史
            }
            
            # 保存文档元数据
            metadata_path = os.path.join(self.data_dir, f'{document_id}.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
            
            if progress_callback:
                progress_callback(document_id, 100, "PDF处理完成！")
            
            return {
                'success': True,
                'document_id': document_id,
                'total_pages': len(images),
                'file_size': file_size
            }
            
        except Exception as e:
            if progress_callback:
                progress_callback(document_id if 'document_id' in locals() else None, -1, f"处理失败: {str(e)}")
            return {
                'success': False,
                'error': f'PDF处理失败: {str(e)}'
            }
    
    def _optimize_image(self, image: Image.Image) -> Image.Image:
        """优化图片质量和大小
        
        Args:
            image: PIL图片对象
            
        Returns:
            优化后的图片对象
        """
        # 设置最大尺寸
        max_width = 1200
        max_height = 1600
        
        # 获取原始尺寸
        width, height = image.size
        
        # 计算缩放比例
        scale_w = max_width / width if width > max_width else 1
        scale_h = max_height / height if height > max_height else 1
        scale = min(scale_w, scale_h)
        
        # 如果需要缩放
        if scale < 1:
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 转换为RGB模式（如果不是的话）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
    
    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """获取文档信息
        
        Args:
            document_id: 文档ID
            
        Returns:
            文档信息
        """
        try:
            metadata_path = os.path.join(self.data_dir, f'{document_id}.json')
            
            if not os.path.exists(metadata_path):
                return {
                    'success': False,
                    'error': '文档不存在'
                }
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
            
            return {
                'success': True,
                'document': document_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'获取文档信息失败: {str(e)}'
            }
    
    def get_all_documents(self) -> Dict[str, Any]:
        """获取所有文档列表
        
        Returns:
            文档列表
        """
        try:
            documents = []
            
            # 遍历数据目录中的所有JSON文件
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.data_dir, filename)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            doc_data = json.load(f)
                        
                        # 只返回基本信息
                        documents.append({
                            'id': doc_data['id'],
                            'filename': doc_data['filename'],
                            'total_pages': doc_data['total_pages'],
                            'file_size': doc_data['file_size'],
                            'created_at': doc_data['created_at'],
                            'status': doc_data['status']
                        })
                    except Exception as e:
                        print(f"读取文档 {filename} 失败: {e}")
                        continue
            
            # 按创建时间排序（最新的在前）
            documents.sort(key=lambda x: x['created_at'], reverse=True)
            
            return {
                'success': True,
                'documents': documents
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'获取文档列表失败: {str(e)}'
            }
    
    def get_page_image_path(self, document_id: str, page_number: int) -> str:
        """获取页面图片路径
        
        Args:
            document_id: 文档ID
            page_number: 页码
            
        Returns:
            图片文件路径
        """
        doc_images_dir = os.path.join(self.images_dir, document_id)
        image_filename = f'page_{page_number}.png'
        return os.path.join(doc_images_dir, image_filename)
    
    def update_document_summary(self, document_id: str, summary: str) -> bool:
        """更新文档总结
        
        Args:
            document_id: 文档ID
            summary: 总结内容
            
        Returns:
            是否成功
        """
        try:
            metadata_path = os.path.join(self.data_dir, f'{document_id}.json')
            
            if not os.path.exists(metadata_path):
                return False
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
            
            document_data['summary'] = summary
            document_data['summary_generated_at'] = datetime.now().isoformat()
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"更新文档总结失败: {e}")
            return False
    
    def add_conversation(self, document_id: str, question: str, answer: str, 
                        source_pages: List[int] = None) -> bool:
        """添加对话记录
        
        Args:
            document_id: 文档ID
            question: 问题
            answer: 回答
            source_pages: 来源页面
            
        Returns:
            是否成功
        """
        try:
            metadata_path = os.path.join(self.data_dir, f'{document_id}.json')
            
            if not os.path.exists(metadata_path):
                return False
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
            
            conversation = {
                'id': str(uuid.uuid4()),
                'question': question,
                'answer': answer,
                'source_pages': source_pages or [],
                'timestamp': datetime.now().isoformat()
            }
            
            if 'conversations' not in document_data:
                document_data['conversations'] = []
            
            document_data['conversations'].append(conversation)
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"添加对话记录失败: {e}")
            return False
    
    def get_conversations(self, document_id: str) -> List[Dict[str, Any]]:
        """获取对话历史
        
        Args:
            document_id: 文档ID
            
        Returns:
            对话历史列表
        """
        try:
            metadata_path = os.path.join(self.data_dir, f'{document_id}.json')
            
            if not os.path.exists(metadata_path):
                return []
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
            
            return document_data.get('conversations', [])
            
        except Exception as e:
            print(f"获取对话历史失败: {e}")
            return []
    
    def cleanup_old_files(self, days: int = 30) -> None:
        """清理旧文件
        
        Args:
            days: 保留天数
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.data_dir, filename)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            doc_data = json.load(f)
                        
                        created_at = datetime.fromisoformat(doc_data['created_at'])
                        
                        if created_at < cutoff_date:
                            # 删除文档文件
                            document_id = doc_data['id']
                            
                            # 删除图片目录
                            doc_images_dir = os.path.join(self.images_dir, document_id)
                            if os.path.exists(doc_images_dir):
                                import shutil
                                shutil.rmtree(doc_images_dir)
                            
                            # 删除原始PDF文件
                            if os.path.exists(doc_data['original_path']):
                                os.remove(doc_data['original_path'])
                            
                            # 删除元数据文件
                            os.remove(filepath)
                            
                            print(f"已清理过期文档: {doc_data['filename']}")
                            
                    except Exception as e:
                        print(f"清理文件 {filename} 失败: {e}")
                        continue
                        
        except Exception as e:
            print(f"清理旧文件失败: {e}")