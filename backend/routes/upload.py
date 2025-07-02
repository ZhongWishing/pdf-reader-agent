from flask import Blueprint, request, jsonify, current_app, session
import os
import uuid
import threading
import time
from werkzeug.utils import secure_filename
from backend.services.pdf_processor import PDFProcessor
from backend.utils.session_manager import session_manager
from config import Config

upload_bp = Blueprint('upload', __name__)
pdf_processor = PDFProcessor()

# 进度状态存储
processing_progress = {}

def update_progress(document_id, progress, message):
    """更新处理进度"""
    processing_progress[document_id] = {
        'progress': progress,
        'message': message,
        'timestamp': time.time()
    }

def process_pdf_async(file_path, filename, document_id, session_id):
    """异步处理PDF"""
    try:
        result = pdf_processor.process_pdf(file_path, filename, 
                                         lambda doc_id, prog, msg: update_progress(doc_id, prog, msg))
        
        if result['success']:
            # 将文档与当前会话关联
            if session_id:
                session_manager.add_document_to_session(session_id, result['document_id'])
            
            # 更新最终状态
            processing_progress[document_id] = {
                'progress': 100,
                'message': '处理完成',
                'success': True,
                'document_id': result['document_id'],
                'total_pages': result['total_pages'],
                'file_size': result['file_size']
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
        current_app.logger.error(f"文件上传失败: {str(e)}")
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