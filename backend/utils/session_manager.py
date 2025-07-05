import os
import time
import threading
import json
import shutil
from datetime import datetime, timedelta
from typing import Dict, Set
from config import Config

class SessionManager:
    """会话管理器 - 管理浏览器会话和自动清理"""
    
    def __init__(self):
        self.active_sessions: Dict[str, float] = {}  # session_id -> last_activity_time
        self.session_documents: Dict[str, Set[str]] = {}  # session_id -> document_ids
        self.session_timeout = 1800  # 30分钟无活动则认为会话过期
        self.cleanup_interval = 300  # 每5分钟检查一次过期会话
        self.cleanup_thread = None
        self.running = False
        self._lock = threading.Lock()
        
        # 启动时清理历史记录
        self._cleanup_startup_history()
        
        # 延迟启动清理线程，避免在Flask开发模式重启时冲突
        self._start_delayed_cleanup()
    
    def _cleanup_startup_history(self):
        """启动时清理所有历史记录"""
        try:
            print("正在清理启动前的历史记录...")
            
            # 清理uploads目录中的所有PDF文件
            uploads_dir = Config.UPLOAD_FOLDER
            if os.path.exists(uploads_dir):
                for filename in os.listdir(uploads_dir):
                    if filename.endswith('.pdf'):
                        file_path = os.path.join(uploads_dir, filename)
                        try:
                            os.remove(file_path)
                            print(f"已删除历史上传文件: {filename}")
                        except Exception as e:
                            print(f"删除文件 {filename} 失败: {e}")
            
            # 清理data目录中的所有元数据文件
            data_dir = Config.DATA_FOLDER
            if os.path.exists(data_dir):
                for filename in os.listdir(data_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(data_dir, filename)
                        try:
                            os.remove(file_path)
                            print(f"已删除历史元数据文件: {filename}")
                        except Exception as e:
                            print(f"删除元数据文件 {filename} 失败: {e}")
            
            # 清理images目录中的所有图片文件夹
            images_dir = os.path.join(data_dir, 'images')
            if os.path.exists(images_dir):
                for item in os.listdir(images_dir):
                    item_path = os.path.join(images_dir, item)
                    if os.path.isdir(item_path):
                        try:
                            shutil.rmtree(item_path)
                            print(f"已删除历史图片目录: {item}")
                        except Exception as e:
                            print(f"删除图片目录 {item} 失败: {e}")
            
            # 清理figures目录中的所有Figure截取文件夹
            figures_dir = os.path.join(data_dir, 'figures')
            if os.path.exists(figures_dir):
                for item in os.listdir(figures_dir):
                    item_path = os.path.join(figures_dir, item)
                    if os.path.isdir(item_path):
                        try:
                            shutil.rmtree(item_path)
                            print(f"已删除历史Figure目录: {item}")
                        except Exception as e:
                            print(f"删除Figure目录 {item} 失败: {e}")
            
            print("历史记录清理完成")
            
        except Exception as e:
            print(f"清理历史记录时出错: {e}")
    
    def _start_delayed_cleanup(self):
        """延迟启动清理线程"""
        def delayed_start():
            time.sleep(5)  # 延迟5秒启动，避免Flask重启冲突
            self.start_cleanup_thread()
        
        delay_thread = threading.Thread(target=delayed_start, daemon=True)
        delay_thread.start()
    
    def start_cleanup_thread(self):
        """启动自动清理线程"""
        with self._lock:
            if not self.running:
                self.running = True
                self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
                self.cleanup_thread.start()
                print("会话管理器已启动，自动清理功能已激活")
    
    def stop_cleanup_thread(self):
        """停止自动清理线程"""
        with self._lock:
            self.running = False
            if self.cleanup_thread and self.cleanup_thread.is_alive():
                try:
                    self.cleanup_thread.join(timeout=2)
                except:
                    pass  # 忽略线程停止时的异常
            print("会话管理器已停止")
    
    def create_session(self, session_id: str) -> str:
        """创建新会话
        
        Args:
            session_id: 会话ID（通常是浏览器生成的唯一标识）
            
        Returns:
            会话ID
        """
        current_time = time.time()
        self.active_sessions[session_id] = current_time
        self.session_documents[session_id] = set()
        print(f"创建新会话: {session_id}")
        return session_id
    
    def update_session_activity(self, session_id: str):
        """更新会话活动时间
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id] = time.time()
        else:
            # 如果会话不存在，创建新会话
            self.create_session(session_id)
    
    def update_session(self, session_id: str):
        """更新会话（别名方法，与update_session_activity功能相同）
        
        Args:
            session_id: 会话ID
        """
        self.update_session_activity(session_id)
    
    def add_document_to_session(self, session_id: str, document_id: str):
        """将文档关联到会话
        
        Args:
            session_id: 会话ID
            document_id: 文档ID
        """
        if session_id not in self.session_documents:
            self.session_documents[session_id] = set()
        
        self.session_documents[session_id].add(document_id)
        self.update_session_activity(session_id)
        print(f"文档 {document_id} 已关联到会话 {session_id}")
    
    def get_session_documents(self, session_id: str) -> Set[str]:
        """获取会话关联的文档
        
        Args:
            session_id: 会话ID
            
        Returns:
            文档ID集合
        """
        return self.session_documents.get(session_id, set())
    
    def get_session_info(self) -> dict:
        """获取会话管理器信息
        
        Returns:
            会话管理器状态信息
        """
        return {
            'active_sessions_count': len(self.active_sessions),
            'total_documents': sum(len(docs) for docs in self.session_documents.values()),
            'session_timeout': self.session_timeout,
            'cleanup_interval': self.cleanup_interval,
            'running': self.running
        }
    
    def is_session_active(self, session_id: str) -> bool:
        """检查会话是否活跃
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否活跃
        """
        if session_id not in self.active_sessions:
            return False
        
        last_activity = self.active_sessions[session_id]
        return (time.time() - last_activity) < self.session_timeout
    
    def cleanup_session(self, session_id: str):
        """清理指定会话的所有数据
        
        Args:
            session_id: 会话ID
        """
        try:
            # 获取会话关联的文档
            document_ids = self.session_documents.get(session_id, set())
            
            print(f"开始清理会话 {session_id}，关联文档数量: {len(document_ids)}")
            
            # 清理每个文档的数据
            for document_id in document_ids:
                self._cleanup_document_data(document_id)
            
            # 从会话记录中移除
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            if session_id in self.session_documents:
                del self.session_documents[session_id]
            
            print(f"会话 {session_id} 清理完成")
            
        except Exception as e:
            print(f"清理会话 {session_id} 时出错: {e}")
    
    def _cleanup_document_data(self, document_id: str):
        """清理单个文档的所有数据
        
        Args:
            document_id: 文档ID
        """
        try:
            # 清理文档元数据文件
            metadata_path = os.path.join(Config.DATA_FOLDER, f'{document_id}.json')
            if os.path.exists(metadata_path):
                # 读取文档信息获取原始文件路径
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                # 删除原始PDF文件
                original_path = doc_data.get('original_path')
                if original_path and os.path.exists(original_path):
                    os.remove(original_path)
                    print(f"已删除原始文件: {original_path}")
                
                # 删除元数据文件
                os.remove(metadata_path)
                print(f"已删除元数据文件: {metadata_path}")
            
            # 清理图片目录
            images_dir = os.path.join(Config.DATA_FOLDER, 'images', document_id)
            if os.path.exists(images_dir):
                shutil.rmtree(images_dir)
                print(f"已删除图片目录: {images_dir}")
            
            # 清理Figure截取图片目录
            figures_dir = os.path.join(Config.DATA_FOLDER, 'figures', document_id)
            if os.path.exists(figures_dir):
                shutil.rmtree(figures_dir)
                print(f"已删除Figure目录: {figures_dir}")
            
            print(f"文档 {document_id} 数据清理完成")
            
        except Exception as e:
            print(f"清理文档 {document_id} 数据时出错: {e}")
    
    def _cleanup_loop(self):
        """清理循环 - 在后台线程中运行"""
        while self.running:
            try:
                self._cleanup_expired_sessions()
                # 分段睡眠，以便更快响应停止信号
                for _ in range(self.cleanup_interval):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"清理过程中发生错误: {e}")
                # 发生错误时也要检查运行状态
                for _ in range(min(30, self.cleanup_interval)):
                    if not self.running:
                        break
                    time.sleep(1)
    
    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = []
        
        # 查找过期会话
        for session_id, last_activity in self.active_sessions.items():
            if (current_time - last_activity) > self.session_timeout:
                expired_sessions.append(session_id)
        
        # 清理过期会话
        for session_id in expired_sessions:
            self.cleanup_session(session_id)
    
    def cleanup_all_sessions(self):
        """清理所有会话（用于应用关闭时）"""
        print("开始清理所有会话...")
        session_ids = list(self.active_sessions.keys())
        
        for session_id in session_ids:
            self.cleanup_session(session_id)
        
        print("所有会话清理完成")
        
        # 停止清理线程
        self.stop_cleanup_thread()
    
    def get_session_info(self) -> Dict:
        """获取会话管理器状态信息
        
        Returns:
            状态信息字典
        """
        current_time = time.time()
        active_count = 0
        total_documents = 0
        
        for session_id, last_activity in self.active_sessions.items():
            if (current_time - last_activity) < self.session_timeout:
                active_count += 1
                total_documents += len(self.session_documents.get(session_id, set()))
        
        return {
            'active_sessions': active_count,
            'total_sessions': len(self.active_sessions),
            'total_documents': total_documents,
            'session_timeout': self.session_timeout,
            'cleanup_interval': self.cleanup_interval,
            'running': self.running
        }

# 全局会话管理器实例
session_manager = SessionManager()