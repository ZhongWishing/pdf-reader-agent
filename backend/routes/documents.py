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
        
        # 生成总结 - 使用批量分析方法
        image_paths = []
        
        # 收集所有页面图片路径
        for page_info in document['pages']:
            page_number = page_info['page_number']
            image_path = pdf_processor.get_page_image_path(document_id, page_number)
            
            if os.path.exists(image_path):
                image_paths.append(image_path)
        
        if not image_paths:
            return jsonify({
                'success': False,
                'error': '无法找到文档图片'
            }), 500
        
        # 使用新的直接从图片生成总结的方法
        try:
            summary = qwen_client.generate_document_summary_from_images(image_paths)
        except Exception as e:
            print(f"批量分析失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'文档分析失败: {str(e)}'
            }), 500
        
        # 保存总结
        pdf_processor.update_document_summary(document_id, summary)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'cached': False
        })
        
    except Exception as e:
        print(f"获取文档总结失败: {str(e)}")
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
        print(f"获取文档页面信息失败: {str(e)}")
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
        print(f"获取页面图片失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取页面图片失败: {str(e)}'
        }), 500

@documents_bp.route('/api/documents/<document_id>/pages/<int:page_number>/extract_figure', methods=['POST'])
def extract_figure(document_id, page_number):
    """从页面中提取指定区域的图片（Figure截取）"""
    try:
        # 获取请求参数
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求参数'
            }), 400
        
        # 获取截取区域参数（相对坐标，0-1之间）
        x = data.get('x', 0)  # 左上角x坐标
        y = data.get('y', 0)  # 左上角y坐标
        width = data.get('width', 1)  # 宽度
        height = data.get('height', 1)  # 高度
        figure_name = data.get('figure_name', f'figure_page_{page_number}')  # 图片名称
        
        # 验证参数
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < width <= 1 and 0 < height <= 1):
            return jsonify({
                'success': False,
                'error': '坐标参数必须在0-1之间'
            }), 400
        
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
        
        # 获取原始页面图片路径
        image_path = pdf_processor.get_page_image_path(document_id, page_number)
        
        if not os.path.exists(image_path):
            return jsonify({
                'success': False,
                'error': '页面图片不存在'
            }), 404
        
        # 执行图片截取
        from PIL import Image
        
        # 打开原始图片
        with Image.open(image_path) as img:
            img_width, img_height = img.size
            
            # 计算实际像素坐标
            left = int(x * img_width)
            top = int(y * img_height)
            right = int((x + width) * img_width)
            bottom = int((y + height) * img_height)
            
            # 截取图片
            cropped_img = img.crop((left, top, right, bottom))
            
            # 保存截取的图片
            figures_dir = os.path.join(Config.DATA_FOLDER, 'figures', document_id)
            os.makedirs(figures_dir, exist_ok=True)
            
            figure_filename = f'{figure_name}_page_{page_number}.png'
            figure_path = os.path.join(figures_dir, figure_filename)
            
            cropped_img.save(figure_path, 'PNG')
        
        return jsonify({
            'success': True,
            'message': 'Figure截取成功',
            'figure_path': figure_path,
            'figure_url': f'/api/documents/{document_id}/figures/{figure_filename}',
            'coordinates': {
                'x': x,
                'y': y,
                'width': width,
                'height': height
            }
        })
        
    except Exception as e:
        print(f"Figure截取失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Figure截取失败: {str(e)}'
        }), 500

@documents_bp.route('/api/documents/<document_id>/figures/<figure_filename>', methods=['GET'])
def get_figure(document_id, figure_filename):
    """获取截取的Figure图片"""
    try:
        figures_dir = os.path.join(Config.DATA_FOLDER, 'figures', document_id)
        figure_path = os.path.join(figures_dir, figure_filename)
        
        if not os.path.exists(figure_path):
            return jsonify({
                'success': False,
                'error': 'Figure图片不存在'
            }), 404
        
        return send_file(
            figure_path,
            mimetype='image/png',
            as_attachment=False,
            download_name=figure_filename
        )
        
    except Exception as e:
        print(f"获取Figure图片失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取Figure图片失败: {str(e)}'
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
        print(f"获取对话历史失败: {str(e)}")
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
        print(f"删除文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'删除文档失败: {str(e)}'
        }), 500