import requests
import json
import base64
import os
from typing import List, Dict, Optional, Any
from backend.utils.api_manager import api_manager

class QwenClient:
    """Qwen API客户端"""
    
    def __init__(self):
        """初始化Qwen客户端"""
        self.config = api_manager.get_qwen_config()
        self.api_key = self.config['api_key']
        self.base_url = self.config['base_url']
        self.vision_model = self.config['vision_model']
        self.ocr_model = self.config['ocr_model']
        self.text_model = self.config['text_model']
        self.timeout = self.config['timeout']
        self.max_retries = self.config['max_retries']
        
        if not api_manager.validate_qwen_config():
            raise ValueError("Qwen API配置无效，请检查API密钥和配置")
        
        self.headers = api_manager.get_api_headers('qwen')
    
    def analyze_document_image(self, image_path: str, prompt: str = None, analysis_type: str = 'comprehensive') -> str:
        """分析文档图片
        
        Args:
            image_path: 图片文件路径
            prompt: 自定义提示词
            analysis_type: 分析类型 ('comprehensive', 'ocr', 'visual')
            
        Returns:
            分析结果文本
        """
        return self.analyze_multiple_images([image_path], prompt, analysis_type)
    
    def analyze_multiple_images(self, image_paths: List[str], prompt: str = None, analysis_type: str = 'comprehensive') -> str:
        """批量分析多张文档图片
        
        Args:
            image_paths: 图片文件路径列表
            prompt: 自定义提示词
            analysis_type: 分析类型 ('comprehensive', 'ocr', 'visual')
            
        Returns:
            分析结果文本
        """
        print(f"\n=== 大模型批量文档图片分析请求 ===")
        print(f"图片数量: {len(image_paths)}")
        print(f"分析类型: {analysis_type}")
        print(f"自定义提示词: {'是' if prompt else '否'}")
        
        # 检查图片文件是否存在
        valid_image_paths = []
        for i, image_path in enumerate(image_paths):
            if os.path.exists(image_path):
                valid_image_paths.append(image_path)
                print(f"图片{i+1}: {image_path} - 存在")
            else:
                print(f"图片{i+1}: {image_path} - 不存在，跳过")
        
        if not valid_image_paths:
            print("错误: 没有有效的图片文件")
            print("=== 批量文档图片分析失败 ===\n")
            raise FileNotFoundError("没有有效的图片文件")
        
        print(f"有效图片数量: {len(valid_image_paths)}")
        
        # 根据分析类型选择模型和提示词
        if analysis_type == 'ocr':
            model = self.ocr_model
            default_prompt = f"""请对这{len(valid_image_paths)}个PDF页面进行精确的文字识别和提取，包括：
1. 提取所有可见的文字内容，保持原有格式和结构
2. 识别数学公式、符号和特殊字符
3. 识别表格结构和数据
4. 标注文字的位置信息（如标题、正文、注释等）
5. 保持文字的层次结构和逻辑关系
6. 按页面顺序组织内容，明确标注每页的内容
7. 使用markdown格式进行文本输出，确保前端渲染效果

【可追溯性要求】
- 对于每个识别的内容段落，请明确标注其来源页面位置
- 格式：[第X页] 具体内容
- 确保重要信息都能追溯到具体的页面和位置

请确保提取的文字准确无误，并用中文描述页面结构。"""
        elif analysis_type == 'visual':
            model = self.vision_model
            default_prompt = f"""请对这{len(valid_image_paths)}个PDF页面进行全面的视觉理解和分析，包括：
1. 每个页面的整体布局和设计结构
2. 图表、图像、图形的详细描述和分析
3. 数据可视化内容的解读（如图表数据、趋势等）
4. 页面中的视觉元素关系和逻辑
5. 学术论文特有的元素（如公式、引用、图注等）
6. 页面间的内容连贯性和逻辑关系

【可追溯性要求】
- 对于每个描述的视觉元素，请明确标注其来源页面位置
- 格式：[第X页] 视觉元素描述
- 确保图表、公式等重要元素都能追溯到具体页面

请按页面顺序提供深入的视觉理解分析，用中文回答。"""
        else:  # comprehensive
            model = self.vision_model
            default_prompt = f"""作为专业的学术文档分析专家，你擅长于分析用户提供的学术文献(已经转化为图片格式传递给你)，请对这{len(valid_image_paths)}个PDF页面进行全面深入的分析：

【文字识别与提取】
- 精确提取所有文字内容，包括标题、正文、注释、引用等，你需要基于提取的文字等内容进行学习，用于解答后续的问题
- 识别数学公式、符号、特殊字符，重点在于理解数学公式中各个符号的具体含义，这是用户在意的
- 保持文字的层次结构和格式，使用markdown格式输出

【视觉元素分析】
- 详细理解图表、图像、表格的内容和数据
- 分析图表的类型、数据趋势、关键信息
- 识别流程图、示意图、架构图等的逻辑关系

【学术内容理解】
- 识别论文的章节结构（摘要、引言、方法、结果、结论等）
- 提取关键概念、术语、定义
- 理解研究方法、实验设计、数据分析
- 识别重要的发现、结论、贡献

【内容定位与索引】
- 为重要内容提供精确的位置描述
- 建立内容的逻辑关系和引用链
- 标注可能被用户询问的关键信息点
- 按页面顺序组织分析结果，确保内容的连贯性

【可追溯性要求 - 重要】
- 对于每个分析的内容，必须明确标注其来源页面位置
- 格式：[第X页] 具体内容描述
- 对于重要的概念、公式、图表、结论等，都要提供精确的页面定位
- 确保用户后续提问时，能够追溯到文献的具体段落和句子
- 在分析结果的最后，提供一个"重要内容索引"，列出关键信息及其页面位置

【整体文档理解】
- 分析文档的整体结构和主要内容
- 识别各页面之间的逻辑关系
- 提取文档的核心观点和结论

请用中文提供详细、准确、结构化的分析结果，确保涵盖所有页面的重要信息，并严格遵循可追溯性要求。"""
        
        if not prompt:
            prompt = default_prompt
        
        print(f"使用模型: {model}")
        print(f"提示词长度: {len(prompt)} 字符")
        
        try:
            print("正在读取图片文件...")
            # 构建消息内容
            content = [{
                'type': 'text',
                'text': prompt
            }]
            
            # 添加所有图片
            total_size = 0
            for i, image_path in enumerate(valid_image_paths):
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                total_size += len(image_data)
                print(f"图片{i+1}文件大小: {len(image_data)} 字节")
                
                # 将图片转换为base64
                import base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                content.append({
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/jpeg;base64,{image_base64}'
                    }
                })
            
            print(f"所有图片总大小: {total_size} 字节")
            
            payload = {
                'model': model,
                'messages': [
                    {
                        'role': 'user',
                        'content': content
                    }
                ],
                'max_tokens': 8000,  # 增加最大token数以支持多图片分析
                'temperature': 0.1
            }
            
            print("正在调用大模型API...")
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout  # 使用配置的超时时间
            )
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                analysis_result = result['choices'][0]['message']['content']
                print(f"分析结果长度: {len(analysis_result)} 字符")
                print(f"分析结果预览: {analysis_result[:200]}{'...' if len(analysis_result) > 200 else ''}")
                print("=== 批量文档图片分析完成 ===\n")
                return analysis_result
            else:
                print(f"API请求失败: {response.status_code} - {response.text}")
                print("=== 批量文档图片分析失败 ===\n")
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"批量分析图片失败: {str(e)}")
            print("=== 批量文档图片分析异常 ===\n")
            raise Exception(f"批量分析图片失败: {str(e)}")
    
    def generate_document_summary_from_images(self, image_paths: List[str]) -> str:
        """直接从图片生成文档总结
        
        Args:
            image_paths: 图片文件路径列表
            
        Returns:
            文档总结
        """
        print(f"\n=== 开始从图片生成文档总结 ===")
        print(f"图片数量: {len(image_paths)}")
        
        try:
            # 使用批量图片分析
            batch_analysis = self.analyze_multiple_images(
                image_paths, 
                analysis_type='comprehensive'
            )
            
            # 生成专门的总结提示词
            summary_prompt = f"""作为专业的学术文档分析专家，请基于提供给你的PDF文档（已经按照PDF的顺序分割成顺序的图片）的完整分析结果，生成一个全面深入的文档总结：

【文档概览】
- 文档类型、主题和研究目的
- 作者信息和发表背景（如有）
- 文档的学术价值和意义

【核心内容分析】
- 主要研究问题和假设
- 研究方法和技术路线
- 关键发现和实验结果
- 重要的数据、图表、公式
- 创新点和贡献

【结构化要点】
- 各章节的主要内容
- 重要概念和术语定义
- 关键结论和建议
- 局限性和未来工作方向

【实用信息】
- 可能被用户询问的重点内容
- 重要信息的页面位置提示
- 相关的参考文献和引用

请用中文提供结构化、详细且易于理解的总结，帮助用户快速掌握文档精髓，并且你需要确保文字结构的美观与完整性。

【文档分析结果】
{batch_analysis}

请基于以上完整分析，生成专业的文档总结："""
            
            print("正在生成最终文档总结...")
            
            payload = {
                'model': self.text_model,
                'messages': [
                    {
                        'role': 'user',
                        'content': summary_prompt
                    }
                ],
                'max_tokens': 4000,
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
                summary = result['choices'][0]['message']['content']
                print(f"文档总结生成成功，长度: {len(summary)} 字符")
                print(f"总结预览: {summary[:200]}{'...' if len(summary) > 200 else ''}")
                print("=== 文档总结生成完成 ===\n")
                return summary
            else:
                print(f"总结生成API请求失败: {response.status_code} - {response.text}")
                print("=== 文档总结生成失败 ===\n")
                raise Exception(f"总结生成失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"从图片生成文档总结失败: {str(e)}")
            print("=== 文档总结生成异常 ===\n")
            raise Exception(f"从图片生成文档总结失败: {str(e)}")
    
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
        
        prompt = f"""作为专业的学术文档分析专家，请为以下PDF文档内容生成一个全面深入的总结：

【文档概览】
- 文档类型、主题和研究目的
- 作者信息和发表背景（如有）
- 文档的学术价值和意义

【核心内容分析】
- 主要研究问题和假设
- 研究方法和技术路线
- 关键发现和实验结果
- 重要的数据、图表、公式
- 创新点和贡献

【结构化要点】
- 各章节的主要内容
- 重要概念和术语定义
- 关键结论和建议
- 局限性和未来工作方向

【实用信息】
- 可能被用户询问的重点内容
- 重要信息的页面位置提示
- 相关的参考文献和引用

请用中文提供结构化、详细且易于理解的总结，帮助用户快速掌握文档精髓。

文档内容：
{full_content}"""
        
        try:
            payload = {
                'model': self.text_model,  # 使用最优文本模型生成总结
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 3000,
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
            return f"生成总结失败: {str(e)}"
    
    def answer_question(self, question: str, relevant_pages: List[str], 
                       conversation_history: List[Dict] = None, 
                       page_images: List[str] = None) -> Dict:
        """回答关于文档的问题
        
        Args:
            question: 用户问题
            relevant_pages: 相关页面内容
            conversation_history: 对话历史
            page_images: 相关页面图片路径列表
            
        Returns:
            包含回答内容和相关信息的字典
        """
        if not relevant_pages:
            return {
                'answer': "抱歉，没有找到相关的文档内容来回答您的问题。",
                'answer_type': 'text',
                'source_images': [],
                'confidence': 0.0
            }
        
        # 构建上下文
        context = "\n\n".join(relevant_pages)
        
        # 构建对话历史
        messages = []
        
        # 系统提示
        system_prompt = """你是一个专业的PDF文档解析智能体，具备强大的多模态理解能力，能够精确分析PDF文档中的文字、图表、公式、图像等各种元素。
        我已经将论文PDF按照页面顺序处理为图片，并将此图片按照图片名称有序传递给你。你具有如下能力：

【核心能力与特长】
- 精确的OCR文字识别和语义理解
- 深度的图表、数据可视化分析（柱状图、折线图、散点图、饼图等）
- 复杂数学公式、化学分子式、物理方程的识别与解释
- 图像、示意图、流程图、架构图的详细描述
- 精确的内容定位和页面引用
- 多模态信息的综合整合与关联分析
- 学术文献的结构化理解（摘要、方法、结果、讨论等）

【专业回答标准】
1. 准确性优先：基于文档实际内容提供精确、可验证的回答
2. 详细定位：当用户询问特定内容时，提供精确的页面位置（如"第X页左上角"、"第Y页图2"）
3. 图表专业分析：
   - 描述图表类型、坐标轴、数据趋势
   - 提取关键数值和统计信息
   - 分析数据背后的科学意义
4. 公式深度解读：
   - 识别公式中的每个变量和常数
   - 解释公式的物理/数学含义
   - 说明公式在文档中的应用场景
5. 结构化表达：使用清晰的层次结构，便于理解
6. 学术严谨性：保持客观、准确，避免过度解读

【可追溯性要求 - 核心】
- 对于回答中的每个重要观点、数据、结论，都必须提供精确的文献来源
- 引用格式："根据文档第X页的内容：'具体引用文字'"或"如第X页所述：'原文内容'"
- 对于图表数据，格式："第X页图Y显示：具体数据描述"
- 对于公式，格式："第X页公式Y表明：公式含义及原文描述"
- 确保用户能够通过你的回答直接定位到文献的具体段落和句子
- 在回答末尾提供"参考位置"部分，列出所有引用的页面和具体内容

【特殊功能处理】
- Figure定位请求：当用户询问"Figure X在哪里"时，不仅要说明页码，还要详细描述该图的具体位置和内容特征
- 数据提取：从表格、图表中准确提取数值数据，并标注来源位置
- 内容对比：比较不同页面或章节的相关内容，明确标注各部分来源
- 引用追踪：帮助定位文献引用和参考资料的具体位置
- 方法复现：详细解释实验方法和技术路线，引用原文描述

【输出格式要求】
- 使用中文回答，表达清晰专业，支持markdown格式
- 重要信息用**粗体**标注
- 页面引用格式："(第X页)"
- 图表引用格式："(第X页，图Y/表Z)"
- 公式引用格式："(第X页，公式Y)"
- 原文引用格式："第X页原文：'具体文字内容'"

【质量保证】
- 如果信息不确定，明确说明不确定性
- 如果需要查看原图，明确指出具体页面和区域
- 对于复杂内容，提供分层次的详细解释
- 每个回答都要确保可追溯性，让用户能验证信息来源"""
        
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
        
        # 分析问题类型，确定是否需要图像支持
        needs_visual = self._analyze_question_type(question)
        
        # 检测Figure请求
        figure_request = self._detect_figure_request(question)
        
        # 添加当前问题和文档内容
        if needs_visual and page_images:
            user_content = f"""【文档文字内容】
{context}

【用户问题】
{question}

【分析要求】
请基于上述文档内容深入分析并回答问题。如果问题涉及：
- 图表、图像内容：请详细描述相关视觉元素，并指出具体位置
- 数学公式：请准确解释公式含义和结构
- 具体位置查询：请提供精确的页面定位信息
- 数据分析：请结合图表和文字进行综合分析
- Figure/Table查询：请详细说明图表的位置、内容和特征

特别注意：如果用户询问特定的Figure或Table，请在回答中明确指出：
1. 该图表在第几页
2. 图表在页面中的大致位置（如左上角、右下角、页面中央等）
3. 图表的类型和主要内容
4. 建议用户可以要求截取该图表的具体区域

请提供专业、准确、详细的回答。"""
        else:
            user_content = f"""【文档内容】
{context}

【用户问题】
{question}

请基于上述文档内容提供准确、详细的回答。如果问题涉及特定内容的位置，请指出相关页面。

特别注意：如果用户询问特定的Figure或Table，请在回答中明确指出：
1. 该图表在第几页
2. 图表在页面中的大致位置
3. 图表的类型和主要内容
4. 如果用户需要查看具体图表，可以要求截取该区域"""
        
        messages.append({
            'role': 'user',
            'content': user_content
        })
        
        try:
            # 根据问题类型选择合适的模型
            model = self.vision_model if (needs_visual and page_images) else self.text_model
            
            payload = {
                'model': model,
                'messages': messages,
                'max_tokens': 3000,
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
                answer_content = result['choices'][0]['message']['content']
                
                # 分析回答类型和置信度
                answer_type = self._determine_answer_type(answer_content, question)
                confidence = self._calculate_confidence(answer_content, context)
                
                return {
                    'answer': answer_content,
                    'answer_type': answer_type,
                    'source_images': page_images if page_images else [],
                    'confidence': confidence,
                    'model_used': model
                }
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            return {
                'answer': f"回答问题失败: {str(e)}",
                'answer_type': 'error',
                'source_images': [],
                'confidence': 0.0
            }
    
    def _analyze_question_type(self, question: str) -> bool:
        """分析问题类型，判断是否需要视觉支持
        
        Args:
            question: 用户问题
            
        Returns:
            是否需要视觉支持
        """
        visual_keywords = [
            '图', '表', '图片', '图像', '图表', '示意图', '流程图',
            'figure', 'table', 'chart', 'diagram', 'image',
            '公式', '方程', '数据', '曲线', '柱状图', '饼图'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in visual_keywords)
    
    def _detect_figure_request(self, question: str) -> Dict[str, Any]:
        """检测用户是否请求查看特定的Figure
        
        Args:
            question: 用户问题
            
        Returns:
            包含Figure请求信息的字典
        """
        import re
        
        # 检测Figure相关的关键词模式
        figure_patterns = [
            r'figure\s*(\d+)',
            r'图\s*(\d+)',
            r'第\s*(\d+)\s*图',
            r'图片\s*(\d+)',
            r'fig\s*\.?\s*(\d+)',
            r'表\s*(\d+)',
            r'table\s*(\d+)',
            r'第\s*(\d+)\s*表'
        ]
        
        question_lower = question.lower()
        
        for pattern in figure_patterns:
            match = re.search(pattern, question_lower)
            if match:
                figure_number = match.group(1)
                return {
                    'has_figure_request': True,
                    'figure_number': figure_number,
                    'figure_type': 'figure' if 'fig' in pattern or '图' in pattern else 'table',
                    'original_match': match.group(0)
                }
        
        # 检测一般性的图片查看请求
        view_keywords = ['显示', '展示', '看', '查看', '截取', '提取']
        if any(keyword in question for keyword in view_keywords) and any(keyword in question_lower for keyword in ['图', 'figure', 'table', '表']):
            return {
                'has_figure_request': True,
                'figure_number': None,
                'figure_type': 'general',
                'original_match': None
            }
        
        return {
            'has_figure_request': False,
            'figure_number': None,
            'figure_type': None,
            'original_match': None
        }
    
    def _determine_answer_type(self, answer: str, question: str) -> str:
        """确定回答类型
        
        Args:
            answer: 回答内容
            question: 原问题
            
        Returns:
            回答类型 ('text', 'mixed', 'visual', 'formula')
        """
        if '公式' in answer or '数学' in answer or '计算' in answer:
            return 'formula'
        elif '图' in answer or '表' in answer or '页面' in answer:
            return 'visual'
        elif len(answer) > 500 and ('图' in answer or '表' in answer):
            return 'mixed'
        else:
            return 'text'
    
    def _calculate_confidence(self, answer: str, context: str) -> float:
        """计算回答置信度
        
        Args:
            answer: 回答内容
            context: 文档上下文
            
        Returns:
            置信度分数 (0.0-1.0)
        """
        if '抱歉' in answer or '无法' in answer or '不确定' in answer:
            return 0.3
        elif '根据文档' in answer or '页面' in answer or '具体' in answer:
            return 0.9
        elif len(answer) > 200:
            return 0.8
        else:
            return 0.6
    
    def chat(self, message: str, conversation_history: List[Dict] = None) -> str:
        """通用聊天功能
        
        Args:
            message: 用户消息
            conversation_history: 对话历史
            
        Returns:
            AI回复内容
        """
        try:
            print(f"\n=== 大模型聊天请求 ===")
            print(f"用户问题: {message}")
            print(f"对话历史条数: {len(conversation_history) if conversation_history else 0}")
            
            # 构建消息列表
            messages = []
            
            # 系统提示
            system_prompt = """你是一个智能助手，能够回答各种问题。请用中文回答用户的问题，保持友好、专业的语调。
            
如果用户询问关于PDF文档分析的问题，请提醒用户可以上传PDF文档来获得更专业的文档分析服务。"""
            
            messages.append({
                'role': 'system',
                'content': system_prompt
            })
            
            # 添加对话历史（最近5轮）
            if conversation_history:
                recent_history = conversation_history[-5:]
                print(f"使用最近 {len(recent_history)} 轮对话历史")
                for conv in recent_history:
                    if 'question' in conv and 'answer' in conv:
                        messages.append({
                            'role': 'user',
                            'content': conv['question']
                        })
                        messages.append({
                            'role': 'assistant',
                            'content': conv['answer']
                        })
            
            # 添加当前用户消息
            messages.append({
                'role': 'user',
                'content': message
            })
            
            print(f"发送给大模型的消息数量: {len(messages)}")
            
            payload = {
                'model': self.text_model,
                'messages': messages,
                'max_tokens': 2000,
                'temperature': 0.7
            }
            
            print(f"使用模型: {self.text_model}")
            print("正在调用大模型API...")
            
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']
                print(f"大模型回复: {answer[:200]}{'...' if len(answer) > 200 else ''}")
                print(f"回复长度: {len(answer)} 字符")
                print("=== 聊天请求完成 ===\n")
                return answer
            else:
                print(f"API请求失败: {response.status_code} - {response.text}")
                print("=== 聊天请求失败 ===\n")
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"聊天功能出错: {str(e)}")
            print("=== 聊天请求异常 ===\n")
            return f"抱歉，处理您的消息时出现错误: {str(e)}"
    
    def test_connection(self) -> bool:
        """测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            payload = {
                'model': self.text_model,
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