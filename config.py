import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # Qwen API配置
    QWEN_API_KEY = os.environ.get('QWEN_API_KEY')
    QWEN_API_URL = os.environ.get('QWEN_API_URL') or 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation'
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', '50')) * 1024 * 1024  # 转换为字节
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'backend', 'uploads'))
    DATA_FOLDER = os.environ.get('DATA_FOLDER', os.path.join(os.path.dirname(__file__), 'backend', 'data'))
    
    # 服务器配置
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', 5000))
    
    # 确保上传和数据目录存在
    @staticmethod
    def init_app(app=None):
        """初始化应用配置"""
        # 创建必要的目录
        upload_folder = Config.UPLOAD_FOLDER
        data_folder = Config.DATA_FOLDER
        
        if app:
            upload_folder = app.config.get('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
            data_folder = app.config.get('DATA_FOLDER', Config.DATA_FOLDER)
        
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(data_folder, exist_ok=True)
        
        # 验证必要的环境变量
        qwen_api_key = Config.QWEN_API_KEY
        if app:
            qwen_api_key = app.config.get('QWEN_API_KEY', Config.QWEN_API_KEY)
        
        if not qwen_api_key:
            print("警告: 未设置QWEN_API_KEY环境变量")
    
    @staticmethod
    def init_directories():
        """初始化必要的目录"""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.DATA_FOLDER, exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    FLASK_ENV = 'production'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}