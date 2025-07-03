from flask import Blueprint, request, jsonify, current_app, session
import os
import uuid
import threading
import time
from werkzeug.utils import secure_filename
from backend.services.pdf_processor import PDFProcessor
from backend.services.qwen_client import QwenClient
from backend.utils.session_manager import session_manager
from config import Config

upload_bp = Blueprint('upload', __name__)
pdf_processor = PDFProcessor()
qwen_client = QwenClient()

# 进度状态存储
processing_progress = {}

def update_progress(document_id, progress, message):
    """更新处理进度"""
    processing_progress[document_id] = {
        'progress': progress,
        'message': message,
        'timestamp': time.time()
    }

def generate_document_summary(document_id):
    """生成文档总结
    
    Args:
        document_id: 文档ID
        
    Returns:
        文档总结文本
    """
    try:
        print(f"\n=== 开始生成文档总结 ===")
        print(f"文档ID: {document_id}")
        
        # 获取文档信息
        doc_info = pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            print("获取文档信息失败")
            print("=== 文档总结生成失败 ===\n")
            return None
        
        document = doc_info['document']
        total_pages = document['total_pages']
        print(f"文档名称: {document['filename']}")
        print(f"总页数: {total_pages}")
        
        # 批量分析所有页面图片（根据实际页数）
        print(f"将批量分析所有 {total_pages} 页内容")
        
        # 收集所有图片路径
        image_paths = []
        for page_num in range(1, total_pages + 1):
            image_path = pdf_processor.get_page_image_path(document_id, page_num)
            if os.path.exists(image_path):
                image_paths.append(image_path)
                print(f"添加第 {page_num} 页图片: {image_path}")
            else:
                print(f"第 {page_num} 页图片文件不存在: {image_path}")
        
        if not image_paths:
            print("没有找到任何有效的页面图片")
            print("=== 文档总结生成失败 ===\n")
            return "无法找到文档图片，请检查文档格式。"
        
        print(f"找到 {len(image_paths)} 个有效图片文件")
        
        try:
            # 使用新的直接从图片生成总结的方法
            print("正在从图片直接生成文档总结...")
            summary = qwen_client.generate_document_summary_from_images(image_paths)
            
        except Exception as e:
            print(f"批量分析失败: {str(e)}")
            print("=== 文档总结生成失败 ===\n")
            # 移除current_app.logger调用以避免应用上下文问题
            return f"文档分析失败: {str(e)}"
        
        if summary:
            print(f"文档总结生成成功，长度: {len(summary)} 字符")
            print(f"总结预览: {summary[:100]}{'...' if len(summary) > 100 else ''}")
            print("=== 文档总结生成完成 ===\n")
        else:
            print("文档总结生成失败")
            print("=== 文档总结生成失败 ===\n")
        
        return summary
        
    except Exception as e:
        print(f"生成文档总结异常: {str(e)}")
        print("=== 文档总结生成异常 ===\n")
        return None

def process_pdf_async(file_path, filename, document_id, session_id):
    """异步处理PDF"""
    try:
        result = pdf_processor.process_pdf(file_path, filename, 
                                         lambda doc_id, prog, msg: update_progress(doc_id, prog, msg))
        
        if result['success']:
            # 将文档与当前会话关联
            if session_id:
                session_manager.add_document_to_session(session_id, result['document_id'])
            
            # 更新进度：开始生成文档总结
            update_progress(document_id, 95, "正在生成文档总结...")
            
            # 生成文档总结
            try:
                summary = generate_document_summary(result['document_id'])
                if summary:
                    # 保存总结到文档元数据
                    pdf_processor.update_document_summary(result['document_id'], summary)
                    update_progress(document_id, 98, "文档总结生成完成")
                else:
                    update_progress(document_id, 98, "文档总结生成失败，但PDF处理完成")
            except Exception as e:
                print(f"生成文档总结失败: {str(e)}")
                update_progress(document_id, 98, f"文档总结生成失败: {str(e)}，但PDF处理完成")
            
            # 更新最终状态
            processing_progress[document_id] = {
                'progress': 100,
                'message': '处理完成',
                'success': True,
                'document_id': result['document_id'],
                'total_pages': result['total_pages'],
                'file_size': result['file_size'],
                'filename': filename
            }
        else:
            # 删除上传的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            processing_progress[document_id] = {
                'progress': -1,
                'message': result['error'],
                'success': False
            }
            
    except Exception as e:
        # 删除上传的文件
        if os.path.exists(file_path):
            os.remove(file_path)
        
        processing_progress[document_id] = {
            'progress': -1,
            'message': f'处理失败: {str(e)}',
            'success': False
        }

@upload_bp.route('/api/upload', methods=['POST'])
def upload_file():
    """上传PDF文件"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        # 检查文件类型
        if not _allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': '只支持PDF文件'
            }), 400
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到文件开头
        
        if file_size > Config.MAX_CONTENT_LENGTH:
            return jsonify({
                'success': False,
                'error': f'文件大小不能超过{Config.MAX_CONTENT_LENGTH // (1024*1024)}MB'
            }), 413
        
        # 保存文件
        filename = secure_filename(file.filename)
        
        # 确保文件名唯一
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        # 确保上传目录存在
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        file.save(file_path)
        
        # 处理PDF
        result = pdf_processor.process_pdf(file_path, filename)
        
        if result['success']:
            # 将文档与当前会话关联
            session_id = session.get('session_id')
            if session_id:
                session_manager.add_document_to_session(session_id, result['document_id'])
            
            return jsonify({
                'success': True,
                'message': '文件上传并处理成功',
                'document_id': result['document_id'],
                'total_pages': result['total_pages'],
                'file_size': result['file_size']
            })
        else:
            # 删除上传的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        print(f"文件上传失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'文件上传失败: {str(e)}'
        }), 500

def _allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf'}

@upload_bp.route('/api/upload/with-progress', methods=['POST'])
def upload_file_with_progress():
    """上传PDF文件（带进度）"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        # 检查文件类型
        if not _allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': '只支持PDF文件'
            }), 400
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到文件开头
        
        if file_size > Config.MAX_CONTENT_LENGTH:
            return jsonify({
                'success': False,
                'error': f'文件大小不能超过{Config.MAX_CONTENT_LENGTH // (1024*1024)}MB'
            }), 413
        
        # 保存文件
        filename = secure_filename(file.filename)
        
        # 确保文件名唯一
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        # 确保上传目录存在
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        file.save(file_path)
        
        # 生成处理ID
        document_id = str(uuid.uuid4())
        
        # 初始化进度
        processing_progress[document_id] = {
            'progress': 0,
            'message': '文件上传完成，准备处理...',
            'timestamp': time.time()
        }
        
        # 获取会话ID
        session_id = session.get('session_id')
        
        # 启动异步处理
        thread = threading.Thread(
            target=process_pdf_async,
            args=(file_path, filename, document_id, session_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '文件上传成功，开始处理',
            'document_id': document_id
        })
        
    except Exception as e:
        current_app.logger.error(f"文件上传失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'文件上传失败: {str(e)}'
        }), 500

@upload_bp.route('/api/upload/progress/<document_id>', methods=['GET'])
def get_upload_progress(document_id):
    """获取上传处理进度"""
    try:
        if document_id not in processing_progress:
            return jsonify({
                'success': False,
                'error': '未找到处理记录'
            }), 404
        
        progress_info = processing_progress[document_id]
        
        # 如果处理完成，清理进度记录（延迟清理）
        if progress_info.get('progress') == 100 or progress_info.get('progress') == -1:
            # 5分钟后清理
            if time.time() - progress_info.get('timestamp', 0) > 300:
                del processing_progress[document_id]
        
        return jsonify({
            'success': True,
            'progress': progress_info
        })
        
    except Exception as e:
        current_app.logger.error(f"获取进度失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取进度失败: {str(e)}'
        }), 500

@upload_bp.route('/api/upload/status', methods=['GET'])
def upload_status():
    """获取上传状态"""
    return jsonify({
        'success': True,
        'max_file_size': Config.MAX_CONTENT_LENGTH,
        'allowed_extensions': ['pdf'],
        'upload_folder': Config.UPLOAD_FOLDER
    })