from flask import Flask, jsonify, send_from_directory, redirect, url_for, request, session
from flask_cors import CORS
import os
import sys
import uuid

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from backend.utils.session_manager import session_manager

def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # 初始化扩展
    CORS(app)
    
    # 设置会话密钥
    app.secret_key = os.environ.get('SECRET_KEY', 'pdf-reader-agent-secret-key-2024')
    
    # 初始化应用配置
    config[config_name].init_app(app)
    
    # 注册会话管理中间件
    register_session_middleware(app)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 健康检查路由
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查接口"""
        return jsonify({
            'success': True,
            'message': 'PDF文档解读智能体服务正常运行',
            'version': '1.0.0'
        })
    
    # 会话管理路由
    @app.route('/api/session/info', methods=['GET'])
    def session_info():
        """获取会话信息"""
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': '会话不存在'
            }), 400
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_manager_info': session_manager.get_session_info()
        })
    
    @app.route('/api/session/cleanup', methods=['POST'])
    def manual_cleanup():
        """手动清理当前会话"""
        session_id = session.get('session_id')
        if session_id:
            session_manager.cleanup_session(session_id)
            session.clear()
            return jsonify({
                'success': True,
                'message': '会话已清理'
            })
        
        return jsonify({
            'success': False,
            'error': '没有活跃的会话'
        }), 400
    
    # 静态文件服务
    @app.route('/')
    def index():
        """主页重定向到前端页面"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(frontend_dir, 'index.html')
    
    @app.route('/<path:filename>')
    def static_files(filename):
        """静态文件服务"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(frontend_dir, filename)
    
    @app.route('/css/<path:filename>')
    def css_files(filename):
        """CSS文件服务"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(os.path.join(frontend_dir, 'css'), filename)
    
    @app.route('/js/<path:filename>')
    def js_files(filename):
        """JavaScript文件服务"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(os.path.join(frontend_dir, 'js'), filename)
    
    @app.route('/assets/<path:filename>')
    def asset_files(filename):
        """资源文件服务"""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(os.path.join(frontend_dir, 'assets'), filename)
    
    return app

def register_blueprints(app):
    """注册蓝图"""
    # 导入并注册蓝图
    try:
        from backend.routes.upload import upload_bp
        app.register_blueprint(upload_bp)
    except ImportError as e:
        print(f"警告: upload蓝图未找到 - {e}")
    
    try:
        from backend.routes.documents import documents_bp
        app.register_blueprint(documents_bp)
    except ImportError as e:
        print(f"警告: documents蓝图未找到 - {e}")
    
    try:
        from backend.routes.chat import chat_bp
        app.register_blueprint(chat_bp)
    except ImportError as e:
        print(f"警告: chat蓝图未找到 - {e}")

def register_session_middleware(app):
    """注册会话管理中间件"""
    @app.before_request
    def before_request():
        # 为每个请求创建或更新会话
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session_manager.create_session(session['session_id'])
        else:
            session_manager.update_session(session['session_id'])

def register_error_handlers(app):
    """注册错误处理器"""
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': '请求的资源不存在',
            'code': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': '服务器内部错误',
            'code': 500
        }), 500
    
    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({
            'success': False,
            'error': '文件大小超过限制（最大50MB）',
            'code': 413
        }), 413
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': '请求参数错误',
            'code': 400
        }), 400



if __name__ == '__main__':
    app = create_app()
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )