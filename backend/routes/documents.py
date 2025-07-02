from flask import Blueprint, jsonify, send_file, current_app
import os
from backend.services.pdf_processor import PDFProcessor
from backend.services.qwen_client import QwenClient
from config import Config

documents_bp = Blueprint('documents', __name__)
pdf_processor = PDFProcessor()
qwen_client = QwenClient()

@documents_bp.route('/api/documents', methods=['GET'])
def get_documents():
    """获取所有文档列表"""
    try:
        result = pdf_processor.get_all_documents()
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"获取文档列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取文档列表失败: {str(e)}'
        }), 500

@documents_bp.route('/api/documents/<document_id>', methods=['GET'])
def get_document(document_id):
    """获取文档详细信息"""
    try:
        result = pdf_processor.get_document_info(document_id)
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"获取文档信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取文档信息失败: {str(e)}'
        }), 500

@documents_bp.route('/api/documents/<document_id>/summary', methods=['GET'])
def get_document_summary(document_id):
    """获取文档总结"""
    try:
        # 获取文档信息
        doc_info = pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            return jsonify(doc_info), 404
        
        document = doc_info['document']
        
        # 检查是否已有总结
        if document.get('summary'):
            return jsonify({
                'success': True,
                'summary': document['summary'],
                'cached': True
            })
        
        # 生成总结
        page_contents = []
        
        # 分析所有页面内容
        for page_info in document['pages']:
            page_number = page_info['page_number']
            image_path = pdf_processor.get_page_image_path(document_id, page_number)
            
            if os.path.exists(image_path):
                try:
                    content = qwen_client.analyze_document_image(
                        image_path, 
                        "请详细分析这个PDF页面的内容，提取所有重要信息，包括文字、数据、图表等。"
                    )
                    page_contents.append(f"第{page_number}页内容：\n{content}")
                except Exception as e:
                    current_app.logger.error(f"分析页面 {page_number} 失败: {str(e)}")
                    continue
        
        if not page_contents:
            return jsonify({
                'success': False,
                'error': '无法分析文档内容'
            }), 500
        
        # 生成总结
        summary = qwen_client.generate_summary(page_contents)
        
        # 保存总结
        pdf_processor.update_document_summary(document_id, summary)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'cached': False
        })
        
    except Exception as e:
        current_app.logger.error(f"获取文档总结失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取文档总结失败: {str(e)}'
        }), 500

@documents_bp.route('/api/documents/<document_id>/pages', methods=['GET'])
def get_document_pages(document_id):
    """获取文档页面信息"""
    try:
        doc_info = pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            return jsonify(doc_info), 404
        
        document = doc_info['document']
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'total_pages': document['total_pages'],
            'pages': document['pages']
        })
        
    except Exception as e:
        current_app.logger.error(f"获取文档页面信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取文档页面信息失败: {str(e)}'
        }), 500

@documents_bp.route('/api/documents/<document_id>/pages/<int:page_number>/image', methods=['GET'])
def get_page_image(document_id, page_number):
    """获取页面图片"""
    try:
        # 获取文档信息
        doc_info = pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            return jsonify(doc_info), 404
        
        document = doc_info['document']
        
        # 检查页码是否有效
        if page_number < 1 or page_number > document['total_pages']:
            return jsonify({
                'success': False,
                'error': '页码无效'
            }), 400
        
        # 获取图片路径
        image_path = pdf_processor.get_page_image_path(document_id, page_number)
        
        if not os.path.exists(image_path):
            return jsonify({
                'success': False,
                'error': '页面图片不存在'
            }), 404
        
        return send_file(
            image_path,
            mimetype='image/png',
            as_attachment=False,
            download_name=f'page_{page_number}.png'
        )
        
    except Exception as e:
        current_app.logger.error(f"获取页面图片失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取页面图片失败: {str(e)}'
        }), 500

@documents_bp.route('/api/documents/<document_id>/conversations', methods=['GET'])
def get_conversations(document_id):
    """获取文档对话历史"""
    try:
        conversations = pdf_processor.get_conversations(document_id)
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'conversations': conversations
        })
        
    except Exception as e:
        current_app.logger.error(f"获取对话历史失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取对话历史失败: {str(e)}'
        }), 500

@documents_bp.route('/api/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """删除文档"""
    try:
        # 获取文档信息
        doc_info = pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            return jsonify(doc_info), 404
        
        document = doc_info['document']
        
        # 删除相关文件
        import shutil
        
        # 删除图片目录
        images_dir = os.path.join(Config.DATA_FOLDER, 'images', document_id)
        if os.path.exists(images_dir):
            shutil.rmtree(images_dir)
        
        # 删除原始PDF文件
        if os.path.exists(document['original_path']):
            os.remove(document['original_path'])
        
        # 删除元数据文件
        metadata_path = os.path.join(Config.DATA_FOLDER, f'{document_id}.json')
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        
        return jsonify({
            'success': True,
            'message': '文档删除成功'
        })
        
    except Exception as e:
        current_app.logger.error(f"删除文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'删除文档失败: {str(e)}'
        }), 500