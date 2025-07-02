import requests
import json
import base64
import os
from typing import List, Dict, Optional
from backend.utils.api_manager import api_manager

class QwenClient:
    """Qwen API客户端"""
    
    def __init__(self):
        """初始化Qwen客户端"""
        self.config = api_manager.get_qwen_config()
        self.api_key = self.config['api_key']
        self.base_url = self.config['base_url']
        self.model = self.config['model']
        self.timeout = self.config['timeout']
        self.max_retries = self.config['max_retries']
        
        if not api_manager.validate_qwen_config():
            raise ValueError("Qwen API配置无效，请检查API密钥和配置")
        
        self.headers = api_manager.get_api_headers('qwen')
    
    def analyze_document_image(self, image_path: str, prompt: str = None) -> str:
        """分析文档图片
        
        Args:
            image_path: 图片文件路径
            prompt: 自定义提示词
            
        Returns:
            分析结果文本
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 默认提示词
        if not prompt:
            prompt = "请详细分析这个PDF页面的内容，包括文字、图表、表格等所有信息。请用中文回答。"
        
        try:
            # 读取图片文件
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 构建请求
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # 将图片转换为base64
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': prompt
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/jpeg;base64,{image_base64}'
                                }
                            }
                        ]
                    }
                ],
                'max_tokens': 2000,
                'temperature': 0.1
            }
            
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"分析图片失败: {str(e)}")
    
    def generate_summary(self, page_contents: List[str]) -> str:
        """生成文档总结
        
        Args:
            page_contents: 各页面内容列表
            
        Returns:
            文档总结
        """
        if not page_contents:
            return "文档内容为空，无法生成总结。"
        
        # 合并所有页面内容
        full_content = "\n\n".join(page_contents)
        
        # 如果内容太长，进行截断
        max_length = 8000  # 控制输入长度
        if len(full_content) > max_length:
            full_content = full_content[:max_length] + "\n\n[内容已截断...]"
        
        prompt = f"""请为以下PDF文档内容生成一个详细的总结，包括：
1. 文档主题和目的
2. 主要内容要点
3. 关键信息和数据
4. 结论或建议（如有）

请用中文回答，总结应该简洁明了但包含重要信息。

文档内容：
{full_content}"""
        
        try:
            payload = {
                'model': 'qwen-plus',  # 使用文本模型生成总结
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 1500,
                'temperature': 0.3
            }
            
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            return f"生成总结失败: {str(e)}"
    
    def answer_question(self, question: str, relevant_pages: List[str], 
                       conversation_history: List[Dict] = None) -> str:
        """回答关于文档的问题
        
        Args:
            question: 用户问题
            relevant_pages: 相关页面内容
            conversation_history: 对话历史
            
        Returns:
            回答内容
        """
        if not relevant_pages:
            return "抱歉，没有找到相关的文档内容来回答您的问题。"
        
        # 构建上下文
        context = "\n\n".join(relevant_pages)
        
        # 构建对话历史
        messages = []
        
        # 系统提示
        system_prompt = """你是一个专业的PDF文档分析助手。请基于提供的文档内容回答用户的问题。

回答要求：
1. 只基于提供的文档内容回答，不要添加文档中没有的信息
2. 如果文档中没有相关信息，请明确说明
3. 回答要准确、详细、有条理
4. 使用中文回答
5. 如果涉及数据或具体信息，请准确引用"""
        
        messages.append({
            'role': 'system',
            'content': system_prompt
        })
        
        # 添加对话历史（最近3轮）
        if conversation_history:
            recent_history = conversation_history[-3:]
            for conv in recent_history:
                messages.append({
                    'role': 'user',
                    'content': conv.get('question', '')
                })
                messages.append({
                    'role': 'assistant',
                    'content': conv.get('answer', '')
                })
        
        # 添加当前问题和文档内容
        user_content = f"""文档内容：
{context}

用户问题：{question}

请基于上述文档内容回答问题。"""
        
        messages.append({
            'role': 'user',
            'content': user_content
        })
        
        try:
            payload = {
                'model': 'qwen-plus',
                'messages': messages,
                'max_tokens': 2000,
                'temperature': 0.2
            }
            
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            return f"回答问题失败: {str(e)}"
    
    def test_connection(self) -> bool:
        """测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            payload = {
                'model': 'qwen-plus',
                'messages': [
                    {
                        'role': 'user',
                        'content': '你好'
                    }
                ],
                'max_tokens': 10
            }
            
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except Exception:
            return False