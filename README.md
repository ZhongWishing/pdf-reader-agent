# PDF文档解读智能体

一个基于Flask和Qwen API的智能PDF文档解读系统，支持PDF文档上传、内容分析、智能问答等功能。

## 功能特性

- 📄 **PDF文档上传与处理**：支持PDF文件上传，自动转换为图片格式
- 🤖 **智能文档分析**：基于Qwen API的文档内容理解和分析
- 💬 **智能问答系统**：针对文档内容进行智能问答
- 📊 **文档总结生成**：自动生成文档摘要和关键信息
- 🔍 **页面智能选择**：根据问题自动选择相关页面进行分析
- 📱 **现代化UI界面**：响应式设计，支持拖拽上传
- 💾 **对话历史记录**：保存和查看历史对话记录

## 技术栈

### 后端
- **Flask**：Web框架
- **pdf2image**：PDF转图片处理
- **Pillow**：图像处理
- **requests**：HTTP请求处理
- **jieba**：中文分词

### 前端
- **原生JavaScript**：前端逻辑
- **CSS3**：现代化样式设计
- **HTML5**：页面结构

### AI服务
- **Qwen API**：文档理解和问答

## 项目结构

```
pdf-reader-agent/
├── backend/                 # 后端代码
│   ├── app.py              # Flask应用主文件
│   ├── routes/             # API路由
│   │   ├── upload.py       # 文件上传路由
│   │   ├── documents.py    # 文档管理路由
│   │   └── chat.py         # 聊天问答路由
│   ├── services/           # 业务服务
│   │   ├── qwen_client.py  # Qwen API客户端
│   │   ├── pdf_processor.py # PDF处理服务
│   │   └── question_analyzer.py # 问题分析服务
│   ├── models/             # 数据模型
│   └── utils/              # 工具函数
├── frontend/               # 前端代码
│   ├── index.html          # 主页面
│   ├── css/
│   │   └── style.css       # 样式文件
│   ├── js/
│   │   └── app.js          # 前端逻辑
│   └── assets/             # 静态资源
├── data/                   # 数据存储目录
├── uploads/                # 文件上传目录
├── venv/                   # Python虚拟环境
├── config.py               # 配置文件
├── requirements.txt        # Python依赖
├── run.py                  # 启动文件
├── .env.example           # 环境变量示例
└── README.md              # 项目说明
```

## 安装与配置

### 1. 环境要求

- Python 3.8+
- pip
- poppler-utils（用于PDF转图片）

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Qwen API配置
QWEN_API_KEY=your_qwen_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-vl-plus

# 应用配置
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your_secret_key_here

# 文件上传配置
MAX_CONTENT_LENGTH=50
UPLOAD_FOLDER=uploads
DATA_FOLDER=data

# 服务器配置
HOST=0.0.0.0
PORT=5000
```

### 4. 安装poppler（Windows）

下载并安装 [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)，将bin目录添加到系统PATH。

## 运行应用

```bash
# 激活虚拟环境
venv\Scripts\activate

# 启动应用
python run.py
```

访问 http://localhost:5000 查看应用。

## API接口

### 健康检查
```
GET /api/health
```

### 文件上传
```
POST /api/upload
Content-Type: multipart/form-data

file: PDF文件
```

### 获取文档列表
```
GET /api/documents
```

### 获取文档信息
```
GET /api/documents/{document_id}
```

### 获取文档总结
```
GET /api/documents/{document_id}/summary
```

### 聊天问答
```
POST /api/chat
Content-Type: application/json

{
  "document_id": "文档ID",
  "question": "用户问题"
}
```

### 获取对话历史
```
GET /api/documents/{document_id}/conversations
```

## 使用说明

1. **上传PDF文档**：点击上传区域或拖拽PDF文件到上传区域
2. **查看文档列表**：在左侧边栏查看已上传的文档
3. **选择文档**：点击文档名称加载文档信息
4. **查看文档总结**：系统自动生成文档摘要
5. **智能问答**：在聊天区域输入问题，获得基于文档内容的回答
6. **查看来源页面**：点击回答中的页面标签查看原始页面

## 开发说明

### 添加新功能

1. 在 `backend/routes/` 中添加新的路由文件
2. 在 `backend/services/` 中添加业务逻辑
3. 在 `backend/app.py` 中注册新的蓝图
4. 更新前端 `frontend/js/app.js` 添加对应功能

### 测试

```bash
# 运行测试
pytest tests/

# 测试API连接
curl http://localhost:5000/api/health
```

## 故障排除

### 常见问题

1. **PDF转换失败**：确保已安装poppler-utils
2. **Qwen API调用失败**：检查API密钥和网络连接
3. **文件上传失败**：检查文件大小和格式
4. **页面无法加载**：检查uploads和data目录权限

### 日志查看

应用日志会输出到控制台，包含详细的错误信息和调试信息。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！