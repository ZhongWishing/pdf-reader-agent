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
    
    def detect_figures_in_page(self, image_path: str, figure_query: str = None) -> Dict:
        """精确检测页面中的Figure位置和信息
        
        Args:
            image_path: 页面图片路径
            figure_query: 用户查询的Figure描述（如"Figure 1", "表格2"等）
            
        Returns:
            包含Figure位置信息的字典
        """
        print(f"\n=== 开始检测页面中的Figure ===")
        print(f"图片路径: {image_path}")
        print(f"查询内容: {figure_query}")
        
        # 构建专门的Figure检测提示词
        detection_prompt = f"""作为专业的文档图像分析专家，请精确分析这个PDF页面中的图表、图像和表格，并提供详细的位置信息。

【重要指令】
{f'用户正在查询特定内容：{figure_query}' if figure_query else '用户需要识别页面中的所有图表元素'}
{f'请ONLY识别和返回与"{figure_query}"完全匹配的图表元素，忽略其他无关图表！' if figure_query else ''}

【分析任务】
1. 识别页面中的视觉元素（重点关注用户查询的特定内容）：
   - 图表（Figure 1, Figure 2等，柱状图、折线图、散点图、饼图等）
   - 表格（Table 1, Table 2等，数据表、对比表等）
   - 图像（照片、示意图、流程图等）
   - 公式（数学公式、化学式等）

2. 为匹配的元素提供精确的位置信息：
   - 元素类型和编号（如"Figure 1", "Table 2"等）
   - 在页面中的相对位置（用百分比表示）
   - 边界框坐标（左上角x,y + 宽度,高度，均为百分比）
   - 元素的标题或说明文字
   - 元素的主要内容描述

【精确定位要求】
- 仔细观察图表的实际边界，包括图表本身、标题、坐标轴、图例等完整内容
- 确保边界框紧密贴合图表的实际范围，不要包含过多空白区域
- 特别注意图表的左上角坐标要准确，避免偏移
- 宽度和高度要覆盖图表的完整内容，包括标题和图例
- 如果图表有标题在上方，边界框应该从标题开始
- 如果图表有图例或说明文字，边界框应该包含这些内容

【置信度评分标准 - 重要】
请根据以下标准为每个检测到的Figure分配置信度分数：

**高置信度 (0.9-1.0)：标准学术Figure格式**
- 彩色图片/图表 + 下方明确的文字标题（如"Figure 1. xxx"）
- 图表内容丰富，有坐标轴、数据点、图例等完整元素
- 标题与图表内容高度相关，描述清晰
- 整体布局规范，符合学术论文标准

**中等置信度 (0.7-0.9)：部分符合Figure格式**
- 有图表但标题不够明确或位置不标准
- 图表为黑白但有完整的标题和说明
- 图表内容较简单但结构完整

**低置信度 (0.5-0.7)：可能的Figure元素**
- 仅有图片但缺少明确标题
- 仅有文字描述但缺少图表
- 图表不完整或模糊

**极低置信度 (0.3-0.5)：疑似Figure**
- 纯文字段落（即使包含"Figure"字样）
- 页面布局元素（页眉、页脚等）
- 不完整或截断的图表

**不是Figure (0.0-0.3)：明确排除**
- 纯文字内容
- 页面装饰元素
- 明显不是图表的内容

【关键要求】
- 论文页面中会有标题（如3.1）等会被误认为是Figure，需要特别注意，这不是用户想要的
- 论文中会有页面的文字部分提及“Figure num”，这是论文对于Figure的讲解，不是用户想要的
- 如果用户查询特定Figure（如"Figure 1"），则ONLY返回该Figure，不要返回其他Figure
- 如果页面中没有用户查询的目标Figure，则返回空的figures数组
- 确保返回的Figure与用户查询完全匹配
- 优先识别有明确标号的Figure和Table
- 定位精度要求：坐标误差应控制在±2%以内
- **严格按照置信度评分标准，优先识别彩色图片+文字标题的标准Figure格式**

【输出格式要求】
请严格按照以下JSON格式输出结果：
```json
{{
  "total_figures": 数量,
  "figures": [
    {{
      "id": "figure_1",
      "type": "图表类型",
      "title": "标题或编号",
      "description": "内容描述",
      "position": {{
        "x": 左上角x坐标百分比,
        "y": 左上角y坐标百分比,
        "width": 宽度百分比,
        "height": 高度百分比
      }},
      "confidence": 置信度(0-1),
      "matches_query": 是否匹配用户查询(true/false)
    }}
  ]
}}
```

【重要说明】
- 坐标系统：左上角为(0,0)，右下角为(100,100)
- 所有数值都用百分比表示，便于后续截取
- 坐标定位要求极高精度，请仔细观察图表的实际边界
- 如果无法确定精确位置，请给出最佳估计并降低置信度
- 如果页面中没有匹配的Figure，请返回空的figures数组
- 只返回与用户查询匹配的Figure，避免截取无关图片
- 特别注意：避免坐标偏移，确保截取的是完整且准确的目标图表
"""
        
        try:
            print("正在读取图片文件...")
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            print(f"图片文件大小: {len(image_data)} 字节")
            
            # 将图片转换为base64
            import base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            payload = {
                'model': self.vision_model,  # 使用最优视觉模型
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': detection_prompt
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
                'max_tokens': 3000,
                'temperature': 0.1  # 低温度确保结果稳定
            }
            
            print("正在调用Figure检测API...")
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                detection_result = result['choices'][0]['message']['content']
                print(f"检测结果长度: {len(detection_result)} 字符")
                
                # 尝试解析JSON结果
                try:
                    import json
                    import re
                    
                    # 提取JSON部分
                    json_match = re.search(r'```json\s*({.*?})\s*```', detection_result, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        figure_data = json.loads(json_str)
                        print(f"成功解析JSON，发现 {figure_data.get('total_figures', 0)} 个图表")
                        print("=== Figure检测完成 ===")
                        return {
                            'success': True,
                            'figures': figure_data.get('figures', []),
                            'total_figures': figure_data.get('total_figures', 0),
                            'raw_response': detection_result
                        }
                    else:
                        print("未找到JSON格式结果，返回原始文本")
                        return {
                            'success': False,
                            'error': 'JSON格式解析失败',
                            'raw_response': detection_result
                        }
                        
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {str(e)}")
                    return {
                        'success': False,
                        'error': f'JSON解析错误: {str(e)}',
                        'raw_response': detection_result
                    }
            else:
                print(f"API请求失败: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'API请求失败: {response.status_code}'
                }
                
        except Exception as e:
            print(f"Figure检测失败: {str(e)}")
            print("=== Figure检测异常 ===")
            return {
                        'success': False,
                        'error': f'Figure检测失败: {str(e)}'
                    }
    
    def review_extracted_figures(self, figure_images: List[Dict], user_query: str) -> Dict:
        """大模型审查截取的Figure图片，选择最符合用户要求的目标Figure
        
        Args:
            figure_images: 截取的Figure图片列表，每个包含image_path和相关信息
            user_query: 用户的原始查询
            
        Returns:
            审查结果，包含推荐的最佳Figure
        """
        print(f"\n=== 开始大模型审查截取的Figure ====")
        print(f"待审查图片数量: {len(figure_images)}")
        print(f"用户查询: {user_query}")
        
        if not figure_images:
            return {
                'success': False,
                'error': '没有图片需要审查',
                'recommended_figure': None
            }
        
        # 构建审查提示词
        review_prompt = f"""作为专业的学术文档分析专家，请审查这些截取的图片，判断哪一个最符合用户的查询要求。

【用户查询】
{user_query}

【审查任务】
请仔细分析每张图片，判断：
1. 图片内容是否与用户查询相关
2. 图片质量和完整性
3. 是否为标准的学术Figure格式（彩色图表 + 文字标题）
4. 图片中的信息是否能回答用户的问题

【评分标准】
为每张图片打分（0-10分）：
- **10分：完美匹配** - 彩色图表 + 清晰标题 + 完全符合用户查询
- **8-9分：高度匹配** - 图表清晰 + 有标题 + 高度相关用户查询
- **6-7分：部分匹配** - 图表可见 + 部分相关用户查询
- **4-5分：勉强匹配** - 图片模糊或相关性较低
- **1-3分：不匹配** - 图片质量差或与查询无关
- **0分：完全不符合** - 纯文字或无关内容

【特别关注】
- 优先选择彩色图表配有明确标题的Figure
- 图表内容应该丰富（有坐标轴、数据点、图例等）
- 标题应该与图表内容高度相关
- 整体布局应该符合学术论文标准
- 不要将一些标题等元素误认为是Figure的标题，你需要严格审查用户要求的目标对象
- 由于上一层截图的不完整性，可能会导致截图中的一部分为目标Figure，但是包含其他内容，你需要严格审查用户要求的目标对象是否在截图中，对于这种情况可以赋予更高的分数

【输出格式】
请严格按照以下JSON格式输出结果：
```json
{{
  "total_reviewed": 图片总数,
  "reviews": [
    {{
      "image_index": 图片索引(0开始),
      "score": 评分(0-10),
      "quality_assessment": "图片质量评估",
      "relevance_assessment": "与查询相关性评估",
      "format_assessment": "Figure格式评估",
      "recommendation_reason": "推荐或不推荐的原因"
    }}
  ],
  "best_figure_index": 最佳图片的索引,
  "confidence": 推荐置信度(0-1),
  "summary": "审查总结和推荐理由"
}}
```

请仔细分析每张图片，给出客观、准确的评估。"""
        
        try:
            print("正在准备图片数据...")
            # 构建消息内容
            content = [{
                'type': 'text',
                'text': review_prompt
            }]
            
            # 添加所有截取的图片
            for i, figure_info in enumerate(figure_images):
                image_path = figure_info.get('image_path')
                if image_path and os.path.exists(image_path):
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    
                    print(f"图片{i+1}: {image_path}, 大小: {len(image_data)} 字节")
                    
                    # 将图片转换为base64
                    import base64
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    content.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_base64}'
                        }
                    })
                else:
                    print(f"警告: 图片{i+1}不存在: {image_path}")
            
            payload = {
                'model': self.vision_model,
                'messages': [
                    {
                        'role': 'user',
                        'content': content
                    }
                ],
                'max_tokens': 2000,
                'temperature': 0.1
            }
            
            print("正在调用大模型进行Figure审查...")
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                review_result = result['choices'][0]['message']['content']
                print(f"审查结果长度: {len(review_result)} 字符")
                
                # 尝试解析JSON结果
                try:
                    import json
                    import re
                    
                    # 提取JSON部分
                    json_match = re.search(r'```json\s*({.*?})\s*```', review_result, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        review_data = json.loads(json_str)
                        
                        best_index = review_data.get('best_figure_index')
                        if best_index is not None and 0 <= best_index < len(figure_images):
                            recommended_figure = figure_images[best_index]
                            print(f"推荐Figure索引: {best_index}, 置信度: {review_data.get('confidence', 0):.2f}")
                            print(f"推荐理由: {review_data.get('summary', 'N/A')}")
                            print("=== Figure审查完成 ===\n")
                            
                            return {
                                'success': True,
                                'recommended_figure': recommended_figure,
                                'review_data': review_data,
                                'raw_response': review_result
                            }
                        else:
                            print("审查结果中没有有效的推荐索引")
                            return {
                                'success': False,
                                'error': '审查结果中没有有效的推荐索引',
                                'raw_response': review_result
                            }
                    else:
                        print("未找到JSON格式的审查结果")
                        return {
                            'success': False,
                            'error': 'JSON格式解析失败',
                            'raw_response': review_result
                        }
                        
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {str(e)}")
                    return {
                        'success': False,
                        'error': f'JSON解析错误: {str(e)}',
                        'raw_response': review_result
                    }
            else:
                print(f"API请求失败: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'API请求失败: {response.status_code}'
                }
                
        except Exception as e:
            print(f"Figure审查失败: {str(e)}")
            print("=== Figure审查异常 ===\n")
            return {
                'success': False,
                'error': f'Figure审查失败: {str(e)}'
            }
    
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

【重要说明】
- 用户询问的“Figure”或者“图”等问题指的是论文文献中的图片等元素，不要理解为我将PDF分割成的、传递给你的论文图片
- 对于论文文献中图表等分析需要具体说明，特别说明图表等与文字内容部分的联系
- 不要过多说明与本问题不相关的其余图表的内容，只需要关注本问题要求的元素即可

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
        # 检测是否是图表相关问题
        is_figure_question = self._analyze_question_type(question)
        
        # 如果没有相关页面内容，检查是否可以通过图片分析来回答图表问题
        if not relevant_pages:
            if is_figure_question and page_images:
                print("检测到图表问题且无文字内容，使用图片进行分析...")
                try:
                    # 使用图片分析来回答图表问题
                    image_analysis = self.analyze_multiple_images(
                        page_images, 
                        prompt=f"请专门针对用户问题'{question}'进行分析，重点关注相关的图表、图像和视觉元素。",
                        analysis_type='visual'
                    )
                    return {
                        'answer': image_analysis,
                        'answer_type': 'visual_analysis',
                        'source_images': page_images,
                        'confidence': 0.8
                    }
                except Exception as e:
                    print(f"图片分析失败: {str(e)}")
                    return {
                        'answer': "抱歉，分析图表内容时出现错误，请稍后重试。",
                        'answer_type': 'error',
                        'source_images': [],
                        'confidence': 0.0
                    }
            else:
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
        
【重要说明】
- 用户询问的“Figure”或者“图”等问题指的是论文文献中的图片等元素，不要理解为我将PDF分割成的、传递给你的论文图片
- 对于论文文献中图表等分析需要具体说明，特别说明图表等与文字内容部分的联系
- 不要过多说明与本问题不相关的其余图表的内容，只需要关注本问题要求的元素即可

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

【重要说明】
- 用户询问的“Figure”或者“图”等问题指的是论文文献中的图片等元素，不要理解为我将PDF分割成的、传递给你的论文图片
- 对于论文文献中图表等分析需要具体说明，特别说明图表等与文字内容部分的联系
- 不要过多说明与本问题不相关的其余图表的内容，只需要关注本问题要求的元素即可

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
            system_prompt = """你是一个专攻于AI领域文献分析的智能助手，能够回答用户上传的文献中的各种相关问题。请用中文回答用户的问题，保持友好、专业的语调。
            
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