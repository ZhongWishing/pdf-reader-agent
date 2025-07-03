#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密钥管理模块
用于集中管理所有API相关的配置和密钥
"""

import os
from dotenv import load_dotenv
from typing import Dict, Optional

# 加载环境变量
load_dotenv()

class APIManager:
    """API密钥和配置管理器"""
    
    def __init__(self):
        """初始化API管理器"""
        self._load_api_configs()
    
    def _load_api_configs(self):
        """加载API配置"""
        # Qwen API配置
        self.qwen_config = {
            'api_key': os.environ.get('QWEN_API_KEY', 'sk-12bce6292cff4499b56ea4dc2ce30082'),
            'base_url': os.environ.get('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
            'vision_model': os.environ.get('QWEN_VISION_MODEL', 'qwen-vl-max-latest'),  # 最优视觉理解模型
            'ocr_model': os.environ.get('QWEN_OCR_MODEL', 'qwen-vl-ocr-latest'),      # 最优文字提取模型
            'text_model': os.environ.get('QWEN_TEXT_MODEL', 'qwen-max-latest'),       # 最优文本理解模型
            'timeout': int(os.environ.get('QWEN_TIMEOUT', '300')),  # 增加到5分钟
            'max_retries': int(os.environ.get('QWEN_MAX_RETRIES', '3'))
        }
        
        # 其他API配置（预留扩展）
        self.other_apis = {
            # 可以添加其他API配置
            # 'openai': {...},
            # 'claude': {...},
        }
    
    def get_qwen_config(self) -> Dict[str, str]:
        """获取Qwen API配置"""
        return self.qwen_config.copy()
    
    def get_qwen_api_key(self) -> str:
        """获取Qwen API密钥"""
        return self.qwen_config['api_key']
    
    def get_qwen_base_url(self) -> str:
        """获取Qwen API基础URL"""
        return self.qwen_config['base_url']
    
    def get_qwen_vision_model(self) -> str:
        """获取Qwen视觉理解模型名称"""
        return self.qwen_config['vision_model']
    
    def get_qwen_ocr_model(self) -> str:
        """获取Qwen OCR模型名称"""
        return self.qwen_config['ocr_model']
    
    def get_qwen_text_model(self) -> str:
        """获取Qwen文本理解模型名称"""
        return self.qwen_config['text_model']
    
    def validate_qwen_config(self) -> bool:
        """验证Qwen API配置是否完整"""
        required_fields = ['api_key', 'base_url', 'vision_model', 'ocr_model', 'text_model']
        
        for field in required_fields:
            if not self.qwen_config.get(field):
                return False
        
        # 检查API密钥格式
        api_key = self.qwen_config['api_key']
        if not api_key.startswith('sk-') or len(api_key) < 20:
            return False
        
        return True
    
    def update_qwen_api_key(self, new_api_key: str) -> bool:
        """更新Qwen API密钥"""
        if not new_api_key or not new_api_key.startswith('sk-'):
            return False
        
        self.qwen_config['api_key'] = new_api_key
        return True
    
    def get_api_headers(self, api_name: str = 'qwen') -> Dict[str, str]:
        """获取API请求头"""
        if api_name == 'qwen':
            return {
                'Authorization': f'Bearer {self.get_qwen_api_key()}',
                'Content-Type': 'application/json'
            }
        
        return {}
    
    def get_config_summary(self) -> Dict[str, any]:
        """获取配置摘要（不包含敏感信息）"""
        qwen_key = self.qwen_config['api_key']
        masked_key = f"{qwen_key[:8]}...{qwen_key[-4:]}" if len(qwen_key) > 12 else "***"
        
        return {
            'qwen': {
                'api_key': masked_key,
                'base_url': self.qwen_config['base_url'],
                'vision_model': self.qwen_config['vision_model'],
                'ocr_model': self.qwen_config['ocr_model'],
                'text_model': self.qwen_config['text_model'],
                'timeout': self.qwen_config['timeout'],
                'max_retries': self.qwen_config['max_retries'],
                'is_valid': self.validate_qwen_config()
            }
        }
    
    @staticmethod
    def create_default_env_file(file_path: str = '.env') -> bool:
        """创建默认的环境变量文件"""
        try:
            env_content = """# Qwen API配置
QWEN_API_KEY=sk-2070ced43347491cb70b298c8a7330c9
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_VISION_MODEL=qwen-vl-max-latest
QWEN_OCR_MODEL=qwen-vl-ocr-latest
QWEN_TEXT_MODEL=qwen-max-latest
QWEN_TIMEOUT=60
QWEN_MAX_RETRIES=3

# 应用配置
FLASK_ENV=development
DEBUG=True
SECRET_KEY=pdf-reader-agent-secret-key-2024

# 文件上传配置
MAX_CONTENT_LENGTH=50
UPLOAD_FOLDER=backend/uploads
DATA_FOLDER=backend/data

# 服务器配置
HOST=0.0.0.0
PORT=5000
"""
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            return True
        except Exception:
            return False

# 全局API管理器实例
api_manager = APIManager()

# 便捷函数
def get_qwen_api_key() -> str:
    """获取Qwen API密钥的便捷函数"""
    return api_manager.get_qwen_api_key()

def get_qwen_config() -> Dict[str, str]:
    """获取Qwen配置的便捷函数"""
    return api_manager.get_qwen_config()

def validate_api_config() -> bool:
    """验证API配置的便捷函数"""
    return api_manager.validate_qwen_config()