#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF文档解读智能体 - 主启动文件
"""

import os
import sys
from flask import Flask
from config import Config
from backend.app import create_app

def main():
    """主函数"""
    try:
        # 初始化目录
        Config.init_directories()
        
        # 创建Flask应用
        app = create_app()
        
        # 启动应用
        print("\n" + "="*50)
        print("PDF文档解读智能体启动中...")
        print("="*50)
        print(f"服务地址: http://localhost:{Config.PORT}")
        print(f"上传目录: {Config.UPLOAD_FOLDER}")
        print(f"数据目录: {Config.DATA_FOLDER}")
        print(f"最大文件大小: {Config.MAX_CONTENT_LENGTH // (1024*1024)}MB")
        print("="*50)
        print("按 Ctrl+C 停止服务")
        print("="*50 + "\n")
        
        # 运行应用
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n\n服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n启动失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()