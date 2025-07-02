from flask import Blueprint, request, jsonify, current_app
import os
from backend.services.pdf_processor import PDFProcessor
from backend.services.qwen_client import QwenClient
from backend.services.question_analyzer import PageSelector

chat_bp = Blueprint('chat', __name__)
pdf_processor = PDFProcessor()
qwen_client = QwenClient()
page_selector = PageSelector(pdf_processor)

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400
        
        document_id = data.get('document_id')
        question = data.get('question', '').strip()
        
        if not document_id:
            return jsonify({
                'success': False,
                'error': '缺少文档ID'
            }), 400
        
        if not question:
            return jsonify({
                'success': False,
                'error': '问题不能为空'
            }), 400
        
        # 获取文档信息
        doc_info = pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            return jsonify({
                'success': False,
                'error': '文档不存在'
            }), 404
        
        # 选择相关页面
        relevant_pages = page_selector.select_relevant_pages(
            document_id, question, max_pages=3
        )
        
        if not relevant_pages:
            return jsonify({
                'success': False,
                'error': '无法找到相关页面'
            }), 500
        
        # 获取页面内容
        page_contents = []
        for page_number in relevant_pages:
            image_path = pdf_processor.get_page_image_path(document_id, page_number)
            
            if os.path.exists(image_path):
                try:
                    # 针对问题优化提示词
                    prompt = f"""请分析这个PDF页面的内容，重点关注与以下问题相关的信息：
问题：{question}

请提取页面中的所有相关信息，包括文字、数据、图表等。"""
                    
                    content = qwen_client.analyze_document_image(image_path, prompt)
                    page_contents.append(f"第{page_number}页内容：\n{content}")
                except Exception as e:
                    current_app.logger.error(f"分析页面 {page_number} 失败: {str(e)}")
                    continue
        
        if not page_contents:
            return jsonify({
                'success': False,
                'error': '无法分析相关页面内容'
            }), 500
        
        # 获取对话历史
        conversation_history = pdf_processor.get_conversations(document_id)
        
        # 生成回答
        answer = qwen_client.answer_question(
            question, 
            page_contents, 
            conversation_history[-5:]  # 只使用最近5轮对话
        )
        
        # 保存对话记录
        pdf_processor.add_conversation(
            document_id, 
            question, 
            answer, 
            relevant_pages
        )
        
        return jsonify({
            'success': True,
            'answer': answer,
            'source_pages': relevant_pages,
            'question': question
        })
        
    except Exception as e:
        current_app.logger.error(f"聊天处理失败: {str(e)}")
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
        current_app.logger.error(f"问题分析失败: {str(e)}")
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
        current_app.logger.error(f"聊天测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'聊天测试失败: {str(e)}'
        }), 500