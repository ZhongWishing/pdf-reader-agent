from flask import Blueprint, request, jsonify, current_app
import os
import re
from backend.services.pdf_processor import PDFProcessor
from backend.services.qwen_client import QwenClient
from backend.services.question_analyzer import PageSelector, QuestionAnalyzer
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

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
        
        # 如果有特定的Figure或Table编号请求，尝试精确匹配
        if figure_request.get('figure_number'):
            figure_num = figure_request['figure_number']
            # 在回答中查找该Figure的具体描述
            figure_desc_pattern = rf'(?:figure|图)\s*{figure_num}[^。]*'
            figure_desc_match = re.search(figure_desc_pattern, answer_text, re.IGNORECASE)
            
            if figure_desc_match:
                # 提取Figure描述，用于后续的精确定位
                figure_description = figure_desc_match.group(0)
                for figure in extracted_figures:
                    figure['description'] = figure_description
                    figure['figure_number'] = figure_num
        elif figure_request.get('table_number'):
            table_num = figure_request['table_number']
            # 在回答中查找该Table的具体描述
            table_desc_pattern = rf'(?:table|表|表格)\s*{table_num}[^。]*'
            table_desc_match = re.search(table_desc_pattern, answer_text, re.IGNORECASE)
            
            if table_desc_match:
                # 提取Table描述，用于后续的精确定位
                table_description = table_desc_match.group(0)
                for figure in extracted_figures:
                    figure['description'] = table_description
                    figure['table_number'] = table_num
        
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

def handle_document_chat(document_id, question, session_id=None):
    """处理文档相关聊天请求"""
    try:
        # 获取文档信息
        doc_info = pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            return jsonify({
                'success': False,
                'error': '文档不存在或已被删除'
            }), 404
        
        document = doc_info['document']
        
        # 分析问题
        question_analyzer = QuestionAnalyzer()
        question_analysis = question_analyzer.analyze_question(question)
        
        # 选择相关页面
        relevant_pages = page_selector.select_relevant_pages(document_id, question)
        
        if not relevant_pages:
            return jsonify({
                'success': False,
                'error': '无法找到相关页面'
            }), 400
        
        # 获取页面内容
        page_contents = page_selector.get_page_content(document_id, relevant_pages)
        
        # 获取页面图片
        page_images = []
        for page_num in relevant_pages:
            image_path = pdf_processor.get_page_image_path(document_id, page_num)
            if os.path.exists(image_path):
                page_images.append({
                    'page': page_num,
                    'image_path': image_path
                })
        
        if not page_images:
            return jsonify({
                'success': False,
                'error': '无法获取页面图片'
            }), 500
        
        # 提取图片路径列表（用于answer_question方法）
        image_paths = [img['image_path'] for img in page_images]
        
        # 使用Qwen分析并回答问题
        answer_result = qwen_client.answer_question(
            question=question,
            relevant_pages=page_contents,
            page_images=image_paths
        )
        
        # 检查是否有错误
        if answer_result.get('answer_type') == 'error':
            return jsonify({
                'success': False,
                'error': f'AI分析失败: {answer_result.get("answer", "未知错误")}'
            }), 500
        
        # 统一的Figure检测和截取逻辑
        auto_extracted_figures = []
        figures_info = []
        
        if question_analysis['figure_info']['has_figure_request']:
            # 构建具体的Figure或Table查询字符串
            figure_query = None
            if question_analysis['figure_info']['figure_numbers']:
                # 如果有具体的编号，根据查询类型构建查询字符串
                figure_num = question_analysis['figure_info']['figure_numbers'][0]
                
                # 检测查询类型：Table还是Figure
                question_lower = question.lower()
                if any(keyword in question_lower for keyword in ['table', '表', '表格']):
                    figure_query = f"Table {figure_num}"
                    print(f"检测到Table查询，构建查询字符串: {figure_query}")
                else:
                    figure_query = f"Figure {figure_num}"
                    print(f"检测到Figure查询，构建查询字符串: {figure_query}")
            elif any(keyword in question.lower() for keyword in ['table', '表', '表格']):
                # Table相关的一般性查询
                figure_query = question
                print(f"检测到Table一般性查询: {figure_query}")
            elif 'figure' in question.lower() or 'fig' in question.lower():
                # Figure相关的一般性查询
                figure_query = question
                print(f"检测到Figure一般性查询: {figure_query}")
            
            print(f"Figure查询: {figure_query}")
            
            # 收集所有检测到的Figure，按置信度排序
            all_detected_figures = []
            
            for page_image in page_images:
                page_num = page_image['page']
                image_path = page_image['image_path']
                
                print(f"正在页面 {page_num} 中搜索目标Figure...")
                
                # 检测页面中的Figure
                detected_figures = qwen_client.detect_figures_in_page(
                    image_path, figure_query
                )
                
                if detected_figures['success'] and detected_figures['figures']:
                    # 只处理匹配查询的Figure
                    matching_figures = [
                        fig for fig in detected_figures['figures'] 
                        if fig.get('matches_query', False) and fig.get('confidence', 0) >= 0.6
                    ]
                    
                    for figure_data in matching_figures:
                        figure_data['page_number'] = page_num
                        figure_data['image_path'] = image_path
                        all_detected_figures.append(figure_data)
                        print(f"在页面 {page_num} 找到匹配Figure: {figure_data.get('title', 'unknown')} (置信度: {figure_data.get('confidence', 0):.2f})")
                else:
                    print(f"页面 {page_num} 中Figure检测失败或无Figure")
            
            # 按置信度降序排序，优先使用置信度最高的Figure
            all_detected_figures.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            if all_detected_figures:
                print(f"\n=== 检测到 {len(all_detected_figures)} 个候选Figure ===")
                
                # 截取所有候选Figure用于审查
                candidate_figures = []
                for i, figure_data in enumerate(all_detected_figures[:3]):  # 最多审查前3个候选
                    page_num = figure_data['page_number']
                    
                    print(f"截取候选Figure {i+1}: 页面{page_num}, 置信度{figure_data.get('confidence', 0):.2f}")
                    
                    # 获取Figure位置信息
                    position = figure_data.get('position', {})
                    x = position.get('x', 0) / 100.0  # 转换为0-1范围
                    y = position.get('y', 0) / 100.0
                    width = position.get('width', 100) / 100.0
                    height = position.get('height', 100) / 100.0
                    
                    # 坐标校正：根据置信度进行微调
                    confidence = figure_data.get('confidence', 0.8)
                    if confidence < 0.9:  # 如果置信度不够高，进行保守的边界扩展
                        margin = 0.02  # 2%的边界扩展
                        x = max(0, x - margin)
                        y = max(0, y - margin)
                        width = min(1 - x, width + 2 * margin)
                        height = min(1 - y, height + 2 * margin)
                    
                    # 确保坐标在有效范围内
                    x = max(0, min(1, x))
                    y = max(0, min(1, y))
                    width = max(0.1, min(1 - x, width))
                    height = max(0.1, min(1 - y, height))
                    
                    # 获取Figure名称
                    figure_name = f"candidate_figure_{i+1}_page_{page_num}_{figure_data.get('id', 'unknown')}"
                    
                    figure_url = auto_extract_figure(
                        document_id, page_num, x, y, width, height, figure_name
                    )
                    
                    if figure_url:
                        # 获取截取图片的完整路径（修正：使用实际的保存路径）
                        figures_dir = os.path.join(Config.DATA_FOLDER, 'figures', document_id)
                        # 从auto_extract_figure返回的URL中提取实际文件名
                        figure_filename = figure_url.split('/')[-1]  # 提取最后的文件名部分
                        figure_path = os.path.join(figures_dir, figure_filename)
                        
                        candidate_info = {
                            'page_number': page_num,
                            'figure_id': figure_data.get('id'),
                            'title': figure_data.get('title'),
                            'type': figure_data.get('type'),
                            'description': figure_data.get('description'),
                            'confidence': figure_data.get('confidence', 0.8),
                            'matches_query': True,
                            'figure_url': figure_url,
                            'image_path': figure_path,  # 用于大模型审查
                            'coordinates': {
                                'x': x, 'y': y, 'width': width, 'height': height
                            },
                            'auto_extracted': True,
                            'candidate_index': i
                        }
                        candidate_figures.append(candidate_info)
                        print(f"成功截取候选Figure {i+1}: {figure_name}")
                    else:
                        print(f"候选Figure {i+1}截取失败: {figure_name}")
                
                # 使用大模型审查机制选择最佳Figure
                if candidate_figures:
                    print(f"\n=== 启动大模型审查机制 ===")
                    print(f"候选Figure数量: {len(candidate_figures)}")
                    
                    review_result = qwen_client.review_extracted_figures(candidate_figures, question)
                    
                    if review_result['success']:
                        # 使用审查推荐的最佳Figure
                        recommended_figure = review_result['recommended_figure']
                        review_data = review_result['review_data']
                        
                        print(f"\n=== 大模型审查完成 ===")
                        print(f"推荐Figure: 候选{recommended_figure['candidate_index']+1}")
                        print(f"审查置信度: {review_data.get('confidence', 0):.2f}")
                        print(f"推荐理由: {review_data.get('summary', 'N/A')}")
                        
                        # 添加审查信息到Figure数据中
                        recommended_figure['review_confidence'] = review_data.get('confidence', 0)
                        recommended_figure['review_summary'] = review_data.get('summary', '')
                        recommended_figure['review_data'] = review_data
                        
                        auto_extracted_figures.append(recommended_figure)
                        print(f"最终选择Figure: {recommended_figure.get('title', 'unknown')}")
                    else:
                        # 如果审查失败，回退到置信度最高的Figure
                        print(f"\n=== 大模型审查失败，回退到置信度排序 ===")
                        print(f"审查失败原因: {review_result.get('error', 'unknown')}")
                        
                        best_figure = candidate_figures[0]  # 第一个就是置信度最高的
                        auto_extracted_figures.append(best_figure)
                        print(f"回退选择Figure: {best_figure.get('title', 'unknown')}")
                else:
                    print("所有候选Figure截取都失败了")
            else:
                print("在所有页面中都没有找到匹配的Figure")
        else:
            # 如果不是Figure查询，使用传统的extract_figures_from_answer方法
            figures_info = extract_figures_from_answer(
                answer_result['answer'], 
                relevant_pages, 
                document_id, 
                question_analysis['figure_info']
            )
        
        response_data = {
            'success': True,
            'answer': answer_result['answer'],
            'relevant_pages': relevant_pages,
            'figures': figures_info,
            'auto_extracted_figures': auto_extracted_figures,
            'question_analysis': question_analysis
        }
        
        # 保存聊天记录
        if session_id:
            session_manager.add_message(
                session_id=session_id,
                message_type='user',
                content=question
            )
            session_manager.add_message(
                session_id=session_id,
                message_type='assistant',
                content=answer_result['answer'],
                metadata={
                    'relevant_pages': relevant_pages,
                    'figures': figures_info,
                    'auto_extracted_figures': auto_extracted_figures
                }
            )
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"处理聊天请求时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'处理请求时出错: {str(e)}'
        }), 500

def analyze_page_figures(image_path, figure_request, page_num, document_id):
    """分析页面中的图表信息并自动截取
    
    Args:
        image_path: 页面图片路径
        figure_request: Figure请求信息
        page_num: 页面号
        document_id: 文档ID
        
    Returns:
        图表信息列表
    """
    try:
        print(f"\n=== 开始分析页面 {page_num} 中的图表 ===")
        
        # 构建查询字符串
        figure_query = None
        if figure_request:
            if 'figure_number' in figure_request:
                figure_query = f"Figure {figure_request['figure_number']}"
            elif 'table_number' in figure_request:
                figure_query = f"Table {figure_request['table_number']}"
            elif 'query_text' in figure_request:
                figure_query = figure_request['query_text']
        
        print(f"Figure查询: {figure_query}")
        
        # 使用新的Figure检测功能
        detection_result = qwen_client.detect_figures_in_page(image_path, figure_query)
        
        extracted_figures = []
        
        if detection_result.get('success') and detection_result.get('figures'):
            print(f"检测到 {len(detection_result['figures'])} 个图表")
            
            for figure_data in detection_result['figures']:
                try:
                    # 检查是否匹配用户查询
                    matches_query = figure_data.get('matches_query', False)
                    confidence = figure_data.get('confidence', 0)
                    boundary_quality = figure_data.get('boundary_quality', 'fair')
                    completeness_check = figure_data.get('completeness_check', {})
                    
                    print(f"Figure质量评估: 置信度={confidence:.2f}, 边界质量={boundary_quality}")
                    print(f"完整性检查: {completeness_check}")
                    
                    # 如果有特定查询，只处理匹配的Figure
                    if figure_query and not matches_query:
                        print(f"跳过不匹配的Figure: {figure_data.get('title', 'unknown')}")
                        continue
                    
                    # 智能质量过滤 - 综合考虑置信度和边界质量
                    def should_process_figure(confidence, boundary_quality, completeness_check):
                        """智能判断是否应该处理这个Figure"""
                        # 基础置信度要求
                        if confidence < 0.5:
                            return False, "置信度过低"
                        
                        # 边界质量检查
                        quality_scores = {
                            'excellent': 1.0,
                            'good': 0.8,
                            'fair': 0.6,
                            'poor': 0.3
                        }
                        quality_score = quality_scores.get(boundary_quality, 0.5)
                        
                        # 完整性检查
                        has_color = completeness_check.get('has_color_content', 'false') == 'true'
                        has_title = completeness_check.get('has_title', 'false') == 'true'
                        element_type = completeness_check.get('element_type', 'figure')
                        
                        # 综合评分 - 根据元素类型调整评分策略
                        if element_type == 'table':
                            # Table评分：主要看结构完整性和标题
                            structure_bonus = 0.1 if has_title else 0
                            final_score = confidence * 0.7 + quality_score * 0.2 + structure_bonus
                        else:
                            # Figure评分：看彩色内容和标题
                            content_bonus = 0.1 if has_color and has_title else 0
                            final_score = confidence * 0.6 + quality_score * 0.3 + content_bonus
                        
                        # 动态阈值：如果有特定查询，降低要求
                        threshold = 0.55 if figure_query else 0.65
                        
                        if final_score >= threshold:
                            return True, f"综合评分通过: {final_score:.2f}"
                        else:
                            return False, f"综合评分不足: {final_score:.2f} < {threshold}"
                    
                    should_process, reason = should_process_figure(confidence, boundary_quality, completeness_check)
                    if not should_process:
                        print(f"跳过Figure: {figure_data.get('title', 'unknown')} - {reason}")
                        continue
                    
                    print(f"处理Figure: {figure_data.get('title', 'unknown')} - {reason}")
                    
                    # 获取Figure位置信息
                    position = figure_data.get('position', {})
                    x = position.get('x', 0) / 100.0  # 转换为0-1范围
                    y = position.get('y', 0) / 100.0
                    width = position.get('width', 100) / 100.0
                    height = position.get('height', 100) / 100.0
                    
                    print(f"原始坐标: x={x:.3f}, y={y:.3f}, w={width:.3f}, h={height:.3f}")
                    
                    # 智能坐标验证和调整
                    def validate_and_adjust_coordinates(x, y, width, height):
                        """验证并智能调整坐标以确保截取完整性"""
                        # 确保坐标在有效范围内
                        x = max(0, min(0.95, x))  # 留出右边界空间
                        y = max(0, min(0.95, y))  # 留出下边界空间
                        
                        # 调整宽度和高度，确保不超出边界且有合理的最小值
                        min_dimension = 0.08  # 最小8%的页面尺寸
                        max_width = min(0.9, 1.0 - x)  # 最大宽度不超过页面且留边距
                        max_height = min(0.9, 1.0 - y)  # 最大高度不超过页面且留边距
                        
                        width = max(min_dimension, min(max_width, width))
                        height = max(min_dimension, min(max_height, height))
                        
                        # 如果调整后的区域太小，尝试向左上方扩展
                        if width < 0.15 or height < 0.15:
                            print("检测到小尺寸区域，尝试智能扩展...")
                            # 向左扩展
                            if x > 0.05 and width < 0.2:
                                expand_left = min(0.05, x)
                                x -= expand_left
                                width += expand_left
                            
                            # 向上扩展
                            if y > 0.05 and height < 0.2:
                                expand_up = min(0.05, y)
                                y -= expand_up
                                height += expand_up
                        
                        return x, y, width, height
                    
                    # 应用智能坐标调整
                    x, y, width, height = validate_and_adjust_coordinates(x, y, width, height)
                    
                    # 额外的Figure特定调整
                    # 为了确保包含完整的Figure标题，适当向下扩展
                    if height < 0.25:  # 如果高度较小，可能遗漏标题
                        title_margin = 0.03  # 为标题预留3%的空间
                        if y + height + title_margin <= 1.0:
                            height += title_margin
                            print(f"为Figure标题预留空间，高度调整为: {height:.3f}")
                    
                    # 为了确保包含完整的彩色图片，适当向上扩展
                    if y > 0.02:  # 如果不是从页面顶部开始，向上扩展一点
                        image_margin = 0.01  # 为图片上边界预留1%的空间
                        y = max(0, y - image_margin)
                        height = min(1.0 - y, height + image_margin)
                        print(f"为彩色图片预留空间，y坐标调整为: {y:.3f}")
                    
                    print(f"Figure位置: x={x:.2f}, y={y:.2f}, w={width:.2f}, h={height:.2f}")
                    print(f"匹配查询: {matches_query}, 置信度: {confidence}")
                    
                    # 自动截取Figure
                    figure_name = figure_data.get('title', f"auto_figure_page_{page_num}_{figure_data.get('id', 'unknown')}")
                    figure_url = auto_extract_figure(
                        document_id, page_num, x, y, width, height, figure_name
                    )
                    
                    if figure_url:
                        figure_info = {
                            'page_number': page_num,
                            'figure_id': figure_data.get('id'),
                            'title': figure_data.get('title'),
                            'type': figure_data.get('type'),
                            'description': figure_data.get('description'),
                            'confidence': confidence,
                            'matches_query': matches_query,
                            'figure_url': figure_url,
                            'coordinates': {
                                'x': x, 'y': y, 'width': width, 'height': height
                            },
                            'auto_extracted': True
                        }
                        extracted_figures.append(figure_info)
                        print(f"成功截取目标Figure: {figure_name}")
                    else:
                        print(f"Figure截取失败: {figure_name}")
                        
                except Exception as e:
                    print(f"处理单个Figure失败: {str(e)}")
                    continue
        else:
            print(f"Figure检测失败: {detection_result.get('error', '未知错误')}")
            # 无论是特定查询还是通用查询，都不返回fallback，避免截取无关图片
            print(f"跳过页面 {page_num}，未检测到匹配的Figure")
        
        print(f"=== 页面 {page_num} 图表分析完成，共提取 {len(extracted_figures)} 个图表 ===")
        return extracted_figures
        
    except Exception as e:
        print(f"分析页面图表失败: {str(e)}")
        current_app.logger.error(f"分析页面图表失败: {str(e)}")
        return []

def auto_extract_figure(document_id, page_number, x, y, width, height, figure_name):
    """自动截取Figure
    
    Args:
        document_id: 文档ID
        page_number: 页面号
        x, y, width, height: 截取区域坐标（0-1范围）
        figure_name: Figure名称
        
    Returns:
        截取的Figure URL，失败返回None
    """
    try:
        print(f"\n=== 开始自动截取Figure ===")
        print(f"文档ID: {document_id}, 页面: {page_number}")
        print(f"截取区域: x={x:.3f}, y={y:.3f}, w={width:.3f}, h={height:.3f}")
        print(f"Figure名称: {figure_name}")
        
        # 获取页面图片路径
        page_image_path = pdf_processor.get_page_image_path(document_id, page_number)
        if not os.path.exists(page_image_path):
            print(f"页面图片不存在: {page_image_path}")
            return None
        
        # 创建figures目录
        figures_dir = os.path.join(Config.DATA_FOLDER, 'figures', document_id)
        os.makedirs(figures_dir, exist_ok=True)
        
        # 生成唯一的文件名
        import time
        timestamp = int(time.time() * 1000)
        safe_figure_name = re.sub(r'[^\w\-_.]', '_', figure_name)
        figure_filename = f"{safe_figure_name}_{timestamp}.png"
        figure_path = os.path.join(figures_dir, figure_filename)
        
        # 使用PIL截取图片
        from PIL import Image
        
        with Image.open(page_image_path) as img:
            img_width, img_height = img.size
            print(f"原始图片尺寸: {img_width} x {img_height}")
            
            # 计算实际像素坐标（使用更精确的浮点计算）
            left = round(x * img_width)
            top = round(y * img_height)
            right = round((x + width) * img_width)
            bottom = round((y + height) * img_height)
            
            print(f"初始计算坐标: ({left}, {top}, {right}, {bottom})")
            
            # 智能边界调整算法 - 确保截取完整性
            def adjust_boundaries_for_completeness(left, top, right, bottom, img_width, img_height):
                """智能调整边界以确保截取完整性"""
                # 设置最小边距，避免截取到边缘像素导致的不完整
                min_margin = 5
                
                # 向外扩展边界以确保完整性（优先保证不遗漏内容）
                expansion_ratio = 0.02  # 向外扩展2%
                
                # 计算扩展量
                width_expansion = max(min_margin, int((right - left) * expansion_ratio))
                height_expansion = max(min_margin, int((bottom - top) * expansion_ratio))
                
                # 向外扩展边界
                adjusted_left = max(0, left - width_expansion)
                adjusted_top = max(0, top - height_expansion)
                adjusted_right = min(img_width, right + width_expansion)
                adjusted_bottom = min(img_height, bottom + height_expansion)
                
                print(f"边界扩展: 左{left}->{adjusted_left}, 上{top}->{adjusted_top}, 右{right}->{adjusted_right}, 下{bottom}->{adjusted_bottom}")
                
                return adjusted_left, adjusted_top, adjusted_right, adjusted_bottom
            
            # 应用智能边界调整
            left, top, right, bottom = adjust_boundaries_for_completeness(left, top, right, bottom, img_width, img_height)
            
            # 确保截取区域有合理的最小尺寸
            min_size = 80  # 增加最小尺寸要求
            if right - left < min_size:
                center_x = (left + right) // 2
                left = max(0, center_x - min_size // 2)
                right = min(img_width, left + min_size)
            
            if bottom - top < min_size:
                center_y = (top + bottom) // 2
                top = max(0, center_y - min_size // 2)
                bottom = min(img_height, top + min_size)
            
            # 最终边界检查
            left = max(0, min(img_width - 1, left))
            top = max(0, min(img_height - 1, top))
            right = max(left + 1, min(img_width, right))
            bottom = max(top + 1, min(img_height, bottom))
            
            print(f"最终截取坐标: ({left}, {top}, {right}, {bottom})")
            print(f"截取区域尺寸: {right - left} x {bottom - top}")
            
            # 截取图片
            cropped_img = img.crop((left, top, right, bottom))
            
            # 检查截取的图片质量
            crop_width, crop_height = cropped_img.size
            if crop_width < 50 or crop_height < 50:
                print(f"警告: 截取的图片过小 ({crop_width}x{crop_height})，可能定位不准确")
            elif crop_width > img_width * 0.9 or crop_height > img_height * 0.9:
                print(f"警告: 截取的图片过大 ({crop_width}x{crop_height})，可能包含过多内容")
            else:
                print(f"截取质量良好: {crop_width}x{crop_height} 像素")
            
            # 保存截取的图片（提高质量）
            cropped_img.save(figure_path, 'PNG', quality=98, optimize=True)
            
        print(f"Figure截取成功: {figure_path}")
        print(f"=== 自动截取Figure完成 ===")
        
        # 返回访问URL
        return f'/api/documents/{document_id}/figures/{figure_filename}'
        
    except Exception as e:
        print(f"自动截取Figure失败: {str(e)}")
        current_app.logger.error(f"自动截取Figure失败: {str(e)}")
        return None

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
        return handle_document_chat(document_id, question)
        

        
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