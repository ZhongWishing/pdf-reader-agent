from flask import Blueprint, request, jsonify, current_app
import os
import re
from backend.services.pdf_processor import PDFProcessor
from backend.services.qwen_client import QwenClient
from backend.services.question_analyzer import PageSelector

chat_bp = Blueprint('chat', __name__)
pdf_processor = PDFProcessor()
qwen_client = QwenClient()
page_selector = PageSelector(pdf_processor)

def extract_figures_from_answer(answer_text, relevant_pages, document_id, figure_request):
    """从回答中提取Figure信息并自动截取相关图片
    
    Args:
        answer_text: AI回答内容
        relevant_pages: 相关页面列表
        document_id: 文档ID
        figure_request: Figure请求信息
        
    Returns:
        提取的图片信息列表
    """
    extracted_figures = []
    
    try:
        # 从回答中解析页面和位置信息
        page_patterns = [
            r'第(\d+)页',
            r'页面(\d+)',
            r'page\s*(\d+)'
        ]
        
        found_pages = set()
        for pattern in page_patterns:
            matches = re.findall(pattern, answer_text, re.IGNORECASE)
            for match in matches:
                found_pages.add(int(match))
        
        # 如果没有找到特定页面，使用相关页面
        if not found_pages:
            found_pages = set(relevant_pages)
        
        # 为每个找到的页面尝试提取图片
        for page_num in found_pages:
            if page_num in relevant_pages:
                # 检查页面图片是否存在
                image_path = pdf_processor.get_page_image_path(document_id, page_num)
                if os.path.exists(image_path):
                     # 分析页面中的图表位置
                     figure_info = analyze_page_figures(image_path, figure_request, page_num, document_id)
                     if figure_info:
                         extracted_figures.extend(figure_info)
        
        # 如果有特定的Figure编号请求，尝试精确匹配
        if figure_request.get('figure_number'):
            figure_num = figure_request['figure_number']
            # 在回答中查找该Figure的具体描述
            figure_desc_pattern = rf'(?:figure|图|表)\s*{figure_num}[^。]*'
            figure_desc_match = re.search(figure_desc_pattern, answer_text, re.IGNORECASE)
            
            if figure_desc_match:
                # 提取Figure描述，用于后续的精确定位
                figure_description = figure_desc_match.group(0)
                for figure in extracted_figures:
                    figure['description'] = figure_description
                    figure['figure_number'] = figure_num
        
    except Exception as e:
        current_app.logger.error(f"提取Figure信息失败: {str(e)}")
    
    return extracted_figures

def handle_general_chat(question):
    """处理无文档的通用聊天"""
    try:
        print(f"开始处理通用聊天...")
        
        # 获取对话历史（通用聊天没有文档ID，使用空字符串）
        print("正在获取通用聊天历史...")
        conversation_history = pdf_processor.get_conversations('')
        print(f"获取到 {len(conversation_history)} 条通用聊天历史")
        
        # 使用Qwen进行通用聊天
        print("正在调用Qwen进行通用聊天...")
        response = qwen_client.chat(question, conversation_history)
        
        if isinstance(response, dict) and response.get('success'):
            print("Qwen通用聊天成功")
            
            # 保存对话记录
            print("正在保存通用聊天记录...")
            pdf_processor.add_conversation(
                '',  # 通用聊天没有文档ID
                question,
                response['answer'],
                []  # 通用聊天没有相关页面
            )
            print("通用聊天记录保存完成")
            print("=== 通用聊天处理成功 ===\n")
            
            return jsonify({
                'success': True,
                'answer': response['answer'],
                'answer_type': 'text',
                'confidence': 0.8,
                'source_pages': [],
                'question': question,
                'model_used': 'qwen-plus',
                'has_figure_request': False,
                'extracted_figures': [],
                'is_general_chat': True
            })
        else:
            # 兼容直接返回字符串的情况
            if isinstance(response, str):
                answer_text = response
                print("Qwen通用聊天成功（字符串格式）")
                
                # 保存对话记录
                print("正在保存通用聊天记录...")
                pdf_processor.add_conversation(
                    '',  # 通用聊天没有文档ID
                    question,
                    answer_text,
                    []  # 通用聊天没有相关页面
                )
                print("通用聊天记录保存完成")
                print("=== 通用聊天处理成功 ===\n")
                
                return jsonify({
                    'success': True,
                    'answer': answer_text,
                    'answer_type': 'text',
                    'confidence': 0.8,
                    'source_pages': [],
                    'question': question,
                    'model_used': 'qwen-plus',
                    'has_figure_request': False,
                    'extracted_figures': [],
                    'is_general_chat': True
                })
            else:
                error_msg = response.get('error', '生成回答失败') if isinstance(response, dict) else '生成回答失败'
                print(f"Qwen通用聊天失败: {error_msg}")
                print("=== 通用聊天处理失败 ===\n")
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
        
    except Exception as e:
        print(f"通用聊天异常: {str(e)}")
        print("=== 通用聊天处理异常 ===\n")
        current_app.logger.error(f"通用聊天失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'聊天失败: {str(e)}'
        }), 500

def analyze_page_figures(image_path, figure_request, page_num, document_id):
    """分析页面中的图表信息
    
    Args:
        image_path: 页面图片路径
        figure_request: Figure请求信息
        page_num: 页面号
        document_id: 文档ID
        
    Returns:
        图表信息列表
    """
    try:
        # 使用Qwen分析页面中的图表
        analysis_prompt = f"""请分析这个PDF页面中的所有图表、图像和表格，并提供以下信息：

1. 图表数量和类型（如：柱状图、折线图、表格、流程图等）
2. 每个图表在页面中的大致位置（如：左上角、右下角、页面中央等）
3. 图表的标题或编号（如：Figure 1, Table 2等）
4. 图表的主要内容描述
5. 建议的截取区域坐标（相对于页面的百分比位置）

请用结构化的格式返回结果。"""
        
        analysis_result = qwen_client.analyze_document_image(
            image_path, analysis_prompt, 'visual'
        )
        
        # 解析分析结果，提取图表信息
        figures = []
        
        # 简化处理：为整个页面创建一个图表条目
        # 在实际应用中，这里可以使用更复杂的图像处理算法来精确定位图表
        figure_info = {
            'page_number': page_num,
            'image_url': f'/api/documents/{document_id}/pages/{page_num}/image',
            'position': 'full_page',  # 暂时返回整页
            'type': figure_request.get('figure_type', 'figure'),
            'analysis': analysis_result,
            'coordinates': {'x': 0, 'y': 0, 'width': 100, 'height': 100}  # 百分比坐标
        }
        
        figures.append(figure_info)
        
        return figures
        
    except Exception as e:
        current_app.logger.error(f"分析页面图表失败: {str(e)}")
        return []

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求"""
    try:
        print(f"\n=== 收到聊天请求 ===")
        
        data = request.get_json()
        
        if not data:
            print("错误: 请求数据为空")
            print("=== 聊天请求处理失败 ===\n")
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400
        
        document_id = data.get('document_id')
        question = data.get('question', '').strip()
        
        if not question:
            print("错误: 问题不能为空")
            print("=== 聊天请求处理失败 ===\n")
            return jsonify({
                'success': False,
                'error': '问题不能为空'
            }), 400
        
        print(f"用户问题: {question}")
        print(f"文档ID: {document_id if document_id else '无（通用聊天）'}")
        
        # 如果没有文档ID，进行通用聊天
        if not document_id:
            print("处理类型: 通用聊天")
            print("=== 开始处理通用聊天 ===\n")
            return handle_general_chat(question)
        
        print("处理类型: 文档相关问答")
        print("=== 开始处理文档聊天 ===\n")
        
        # 获取文档信息
        print(f"正在获取文档信息: {document_id}")
        doc_info = pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            print(f"错误: 文档不存在 - {document_id}")
            print("=== 文档聊天处理失败 ===\n")
            return jsonify({
                'success': False,
                'error': '文档不存在'
            }), 404
        
        print(f"文档信息获取成功: {doc_info.get('filename', 'Unknown')}")
        
        # 选择相关页面
        print(f"正在选择相关页面...")
        relevant_pages = page_selector.select_relevant_pages(
            document_id, question, max_pages=3
        )
        
        if not relevant_pages:
            print("错误: 无法找到相关页面")
            print("=== 文档聊天处理失败 ===\n")
            return jsonify({
                'success': False,
                'error': '无法找到相关页面'
            }), 500
        
        print(f"找到相关页面: {relevant_pages}")
        
        # 获取页面内容和图片路径
        print(f"正在分析页面内容...")
        page_contents = []
        page_images = []
        
        for page_number in relevant_pages:
            image_path = pdf_processor.get_page_image_path(document_id, page_number)
            
            if os.path.exists(image_path):
                try:
                    # 针对问题优化提示词
                    prompt = f"""请深入分析这个PDF页面的内容，重点关注与以下问题相关的信息：

【用户问题】
{question}

【分析要求】
- 提取所有与问题相关的文字、数据、图表信息
- 如果页面包含图表，请详细描述图表内容和数据
- 如果页面包含公式，请准确描述公式结构
- 标注重要信息在页面中的位置
- 建立内容之间的逻辑关系

请提供全面、准确的分析结果。"""
                    
                    # 根据问题类型选择分析方式
                    analysis_type = 'comprehensive'
                    if any(keyword in question.lower() for keyword in ['公式', '数学', '计算']):
                        analysis_type = 'ocr'
                    elif any(keyword in question.lower() for keyword in ['图', '表', '图表', '数据']):
                        analysis_type = 'visual'
                    
                    content = qwen_client.analyze_document_image(
                        image_path, prompt, analysis_type
                    )
                    page_contents.append(f"第{page_number}页内容：\n{content}")
                    page_images.append(image_path)
                except Exception as e:
                    print(f"分析页面 {page_number} 失败: {str(e)}")
                    continue
        
        if not page_contents:
            print("错误: 无法分析相关页面内容")
            print("=== 文档聊天处理失败 ===\n")
            return jsonify({
                'success': False,
                'error': '无法分析相关页面内容'
            }), 500
        
        print(f"页面内容分析完成，共分析了 {len(page_contents)} 个页面")
        
        # 获取对话历史
        print("正在获取对话历史...")
        conversation_history = pdf_processor.get_conversations(document_id)
        print(f"获取到 {len(conversation_history)} 条历史对话")
        
        # 检测Figure请求
        print("正在检测Figure请求...")
        figure_request = qwen_client._detect_figure_request(question)
        print(f"Figure请求检测结果: {figure_request['has_figure_request']}")
        
        # 生成回答
        print("正在生成AI回答...")
        answer_result = qwen_client.answer_question(
            question, 
            page_contents, 
            conversation_history[-5:],  # 只使用最近5轮对话
            page_images  # 传递页面图片路径
        )
        print("AI回答生成完成")
        
        # 处理回答结果
        if isinstance(answer_result, dict):
            answer_text = answer_result.get('answer', '')
            answer_type = answer_result.get('answer_type', 'text')
            confidence = answer_result.get('confidence', 0.0)
            model_used = answer_result.get('model_used', 'unknown')
        else:
            # 兼容旧格式
            answer_text = str(answer_result)
            answer_type = 'text'
            confidence = 0.5
            model_used = 'legacy'
        
        # 如果检测到Figure请求，尝试自动提取相关图片
        extracted_figures = []
        if figure_request['has_figure_request']:
            print("正在自动提取Figure...")
            try:
                extracted_figures = extract_figures_from_answer(
                    answer_text, 
                    relevant_pages, 
                    document_id, 
                    figure_request
                )
                print(f"成功提取 {len(extracted_figures)} 个Figure")
            except Exception as e:
                print(f"自动提取Figure失败: {str(e)}")
        
        # 保存对话记录
        print("正在保存对话记录...")
        pdf_processor.add_conversation(
            document_id, 
            question, 
            answer_text, 
            relevant_pages
        )
        print("对话记录保存完成")
        
        # 构建响应
        response_data = {
            'success': True,
            'answer': answer_text,
            'answer_type': answer_type,
            'confidence': confidence,
            'source_pages': relevant_pages,
            'question': question,
            'model_used': model_used,
            'has_figure_request': figure_request['has_figure_request'],
            'extracted_figures': extracted_figures
        }
        
        # 如果是视觉或混合类型的回答，提供页面图片信息
        if answer_type in ['visual', 'mixed', 'formula'] and page_images:
            response_data['page_images'] = [
                {
                    'page_number': relevant_pages[i],
                    'image_url': f'/api/documents/{document_id}/pages/{relevant_pages[i]}/image'
                }
                for i in range(min(len(relevant_pages), len(page_images)))
            ]
        
        # 如果检测到Figure请求且成功提取了图片，在回答中添加提示
        if figure_request['has_figure_request'] and extracted_figures:
            figure_count = len(extracted_figures)
            figure_info_text = f"\n\n📸 **系统已自动为您提取了 {figure_count} 个相关图表**\n"
            
            for i, figure in enumerate(extracted_figures, 1):
                page_num = figure['page_number']
                figure_type = figure.get('type', 'figure')
                figure_info_text += f"- 图表 {i}: 第{page_num}页的{figure_type}\n"
            
            figure_info_text += "\n您可以在下方查看这些图表的详细内容。"
            response_data['answer'] += figure_info_text
        
        print(f"=== 文档聊天处理成功 ===\n")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"聊天处理异常: {str(e)}")
        print("=== 聊天请求处理异常 ===\n")
        return jsonify({
            'success': False,
            'error': f'处理问题时出现错误: {str(e)}'
        }), 500

@chat_bp.route('/api/chat/analyze', methods=['POST'])
def analyze_question():
    """分析问题（调试用）"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400
        
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'success': False,
                'error': '问题不能为空'
            }), 400
        
        # 分析问题
        from backend.services.question_analyzer import QuestionAnalyzer
        analyzer = QuestionAnalyzer()
        analysis = analyzer.analyze_question(question)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        print(f"问题分析失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'问题分析失败: {str(e)}'
        }), 500

@chat_bp.route('/api/chat/test', methods=['GET'])
def test_chat():
    """测试聊天功能"""
    try:
        # 测试Qwen连接
        connection_ok = qwen_client.test_connection()
        
        return jsonify({
            'success': True,
            'qwen_connection': connection_ok,
            'message': '聊天功能正常' if connection_ok else 'Qwen连接失败'
        })
        
    except Exception as e:
        print(f"聊天测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'聊天测试失败: {str(e)}'
        }), 500