// PDF文档解读智能体 - 前端应用
class PDFReaderApp {
    constructor() {
        this.currentDocument = null;
        this.isProcessing = false;
        this.messageQueue = [];
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.setupSessionCleanup();
        this.checkServerHealth();
        this.loadDocuments();
        this.addWelcomeMessage();
    }
    
    // 设置事件监听器
    setupEventListeners() {
        // 文件上传相关
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // 拖拽上传
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });
        
        // 聊天相关
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendButton');
        
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        sendButton.addEventListener('click', () => this.sendMessage());
        
        // 模态框关闭
        document.getElementById('imageModal').addEventListener('click', (e) => {
            if (e.target.id === 'imageModal') {
                e.target.style.display = 'none';
            }
        });
    }
    
    // 键盘快捷键
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter 发送消息
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
            
            // Escape 关闭模态框
            if (e.key === 'Escape') {
                const modal = document.getElementById('imageModal');
                if (modal.style.display === 'flex') {
                    modal.style.display = 'none';
                }
            }
        });
    }
    
    // 设置会话清理机制
    setupSessionCleanup() {
        // 只在浏览器真正关闭时清理会话（移除页面隐藏等过于频繁的触发）
        window.addEventListener('beforeunload', () => {
            // 只在用户确实要离开页面时清理
            this.cleanupSession();
        });
    }
    
    // 清理当前会话
    async cleanupSession() {
        try {
            // 使用 sendBeacon 确保在页面卸载时也能发送请求
            if (navigator.sendBeacon) {
                navigator.sendBeacon('/api/session/cleanup', JSON.stringify({}));
            } else {
                // 降级方案：使用同步请求
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/session/cleanup', false);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.send(JSON.stringify({}));
            }
        } catch (error) {
            console.warn('会话清理失败:', error);
        }
    }
    
    // 检查服务器健康状态
    async checkServerHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            if (data.success) {
                console.log('服务器连接正常');
            }
        } catch (error) {
            console.error('服务器连接失败:', error);
            this.showError('无法连接到服务器，请检查服务是否启动');
        }
    }
    
    // 处理文件选择
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.handleFileUpload(file);
        }
    }
    
    // 处理文件上传
    async handleFileUpload(file) {
        // 验证文件类型
        if (file.type !== 'application/pdf') {
            this.showError('请选择PDF文件');
            return;
        }
        
        // 验证文件大小 (50MB)
        if (file.size > 50 * 1024 * 1024) {
            this.showError('文件大小不能超过50MB');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        // 显示上传进度
        this.showUploadProgress();
        
        try {
            // 使用带进度的上传API
            const response = await fetch('/api/upload/with-progress', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 开始监控处理进度
                this.monitorProcessingProgress(data.document_id);
            } else {
                this.hideUploadProgress();
                this.showError(data.error || '上传失败');
            }
        } catch (error) {
            this.hideUploadProgress();
            this.showError('上传失败: ' + error.message);
        }
    }
    
    // 显示上传进度
    showUploadProgress() {
        const progressDiv = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        progressDiv.style.display = 'block';
        progressText.textContent = '上传中...';
        progressFill.style.width = '0%';
    }
    
    // 监控处理进度
    async monitorProcessingProgress(documentId) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        const checkProgress = async () => {
            try {
                const response = await fetch(`/api/upload/progress/${documentId}`);
                const data = await response.json();
                
                if (data.success) {
                    const progress = data.progress;
                    
                    // 更新进度条
                    progressFill.style.width = Math.max(0, progress.progress) + '%';
                    progressText.textContent = progress.message;
                    
                    if (progress.progress === 100 && progress.success) {
                        // 处理完成
                        setTimeout(() => {
                            this.hideUploadProgress();
                            this.showSuccess('PDF处理完成！');
                            this.loadDocuments().then(() => {
                                this.loadDocument(progress.document_id);
                            });
                        }, 1000);
                    } else if (progress.progress === -1 || progress.success === false) {
                        // 处理失败
                        this.hideUploadProgress();
                        this.showError(progress.message || '处理失败');
                    } else {
                        // 继续监控
                        setTimeout(checkProgress, 1000);
                    }
                } else {
                    this.hideUploadProgress();
                    this.showError('获取进度失败');
                }
            } catch (error) {
                console.error('监控进度失败:', error);
                this.hideUploadProgress();
                this.showError('监控进度失败');
            }
        };
        
        // 开始监控
        checkProgress();
    }
    
    // 隐藏上传进度
    hideUploadProgress() {
        const progressDiv = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        
        progressFill.style.width = '100%';
        
        setTimeout(() => {
            progressDiv.style.display = 'none';
            progressFill.style.width = '0%';
        }, 500);
    }
    
    // 加载文档列表
    async loadDocuments() {
        try {
            const response = await fetch('/api/documents');
            const data = await response.json();
            
            if (data.success) {
                this.renderDocumentList(data.documents);
            }
        } catch (error) {
            console.error('加载文档列表失败:', error);
        }
    }
    
    // 渲染文档列表
    renderDocumentList(documents) {
        const documentList = document.getElementById('documentList');
        
        if (documents.length === 0) {
            documentList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📂</div>
                    <p>暂无文档</p>
                </div>
            `;
            return;
        }
        
        documentList.innerHTML = documents.map(doc => `
            <div class="document-item" onclick="app.loadDocument('${doc.id}')">
                <div class="doc-name">${doc.filename}</div>
                <div class="doc-meta">
                    <span>${doc.total_pages}页</span>
                    <span>${this.formatFileSize(doc.file_size)}</span>
                </div>
            </div>
        `).join('');
    }
    
    // 加载文档
    async loadDocument(documentId) {
        try {
            // 更新当前文档
            this.currentDocument = { id: documentId };
            
            // 获取文档信息
            const docResponse = await fetch(`/api/documents/${documentId}`);
            const docData = await docResponse.json();
            
            if (docData.success) {
                this.currentDocument = docData.document;
                this.renderDocumentInfo(docData.document);
                
                // 高亮当前文档
                this.highlightCurrentDocument(documentId);
                
                // 启用聊天输入
                this.enableChatInput();
                
                // 获取文档总结
                await this.loadDocumentSummary(documentId);
                
                // 加载对话历史
                await this.loadConversations(documentId);
            }
        } catch (error) {
            console.error('加载文档失败:', error);
            this.showError('加载文档失败');
        }
    }
    
    // 渲染文档信息
    renderDocumentInfo(document) {
        const documentInfo = document.getElementById('documentInfo');
        const docTitle = document.getElementById('docTitle');
        const docPages = document.getElementById('docPages');
        const docSize = document.getElementById('docSize');
        
        docTitle.textContent = document.filename;
        docPages.textContent = `${document.total_pages}页`;
        docSize.textContent = this.formatFileSize(document.file_size);
        
        documentInfo.style.display = 'block';
    }
    
    // 加载文档总结
    async loadDocumentSummary(documentId) {
        const summaryContent = document.getElementById('summaryContent');
        summaryContent.innerHTML = '<div class="loading-summary">正在生成总结...</div>';
        
        try {
            const response = await fetch(`/api/documents/${documentId}/summary`);
            const data = await response.json();
            
            if (data.success) {
                summaryContent.textContent = data.summary;
            } else {
                summaryContent.innerHTML = '<div class="error-summary">总结生成失败</div>';
            }
        } catch (error) {
            console.error('加载总结失败:', error);
            summaryContent.innerHTML = '<div class="error-summary">总结加载失败</div>';
        }
    }
    
    // 高亮当前文档
    highlightCurrentDocument(documentId) {
        // 移除所有高亮
        document.querySelectorAll('.document-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // 添加当前文档高亮
        const currentItem = document.querySelector(`[onclick="app.loadDocument('${documentId}')"]`);
        if (currentItem) {
            currentItem.classList.add('active');
        }
    }
    
    // 启用聊天输入
    enableChatInput() {
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendButton');
        
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.placeholder = '请输入您关于文档的问题...';
    }
    
    // 发送消息
    async sendMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();
        
        if (!message || !this.currentDocument || this.isProcessing) return;
        
        this.isProcessing = true;
        this.updateSendButton(false);
        
        // 添加用户消息
        this.addMessage(message, 'user');
        chatInput.value = '';
        
        // 添加加载消息
        const loadingId = this.addMessage('正在分析您的问题...', 'assistant', true);
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_id: this.currentDocument.id,
                    question: message
                })
            });
            
            const data = await response.json();
            
            // 移除加载消息
            this.removeMessage(loadingId);
            
            if (data.success) {
                this.addMessage(data.answer, 'assistant', false, data.source_pages);
            } else {
                this.addMessage(
                    `抱歉，处理您的问题时出现错误：${data.error}`, 
                    'assistant', 
                    false, 
                    null, 
                    'error'
                );
            }
            
        } catch (error) {
            console.error('发送消息失败:', error);
            this.removeMessage(loadingId);
            this.addMessage(
                '网络连接出现问题，请检查网络后重试。', 
                'assistant', 
                false, 
                null, 
                'error'
            );
        } finally {
            this.isProcessing = false;
            this.updateSendButton(true);
        }
    }
    
    // 添加消息
    addMessage(content, type, isLoading = false, sourcePages = null, messageType = 'normal') {
        const chatMessages = document.getElementById('chatMessages');
        const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type} ${messageType}`;
        messageDiv.id = messageId;
        
        let sourceHtml = '';
        if (sourcePages && sourcePages.length > 0) {
            sourceHtml = '<div class="source-pages">📄 来源页面: ';
            sourcePages.forEach(page => {
                sourceHtml += `<span class="source-page" onclick="app.showPageImage('${this.currentDocument.id}', ${page})">第${page}页</span> `;
            });
            sourceHtml += '</div>';
        }
        
        const timestamp = new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="message-content ${isLoading ? 'loading' : ''}">
                ${content}
                ${sourceHtml}
                <div class="message-time">${timestamp}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageId;
    }
    
    // 移除消息
    removeMessage(messageId) {
        const message = document.getElementById(messageId);
        if (message) {
            message.remove();
        }
    }
    
    // 更新发送按钮状态
    updateSendButton(enabled) {
        const sendButton = document.getElementById('sendButton');
        const chatInput = document.getElementById('chatInput');
        
        sendButton.disabled = !enabled;
        chatInput.disabled = !enabled;
        
        if (enabled) {
            sendButton.textContent = '发送';
            chatInput.placeholder = '请输入您关于文档的问题...';
        } else {
            sendButton.textContent = '处理中...';
            chatInput.placeholder = '正在处理中，请稍候...';
        }
    }
    
    // 滚动到底部
    scrollToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    // 显示页面图片
    async showPageImage(documentId, pageNumber) {
        try {
            this.showImageLoading();
            
            const response = await fetch(`/api/documents/${documentId}/pages/${pageNumber}/image`);
            
            if (response.ok) {
                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);
                
                document.getElementById('modalImage').src = imageUrl;
                document.getElementById('modalPageInfo').innerHTML = `
                    <strong>第${pageNumber}页</strong>
                `;
                document.getElementById('imageModal').style.display = 'flex';
                
                // 清理URL
                setTimeout(() => URL.revokeObjectURL(imageUrl), 60000);
            } else {
                throw new Error('页面图片加载失败');
            }
        } catch (error) {
            console.error('加载页面图片失败:', error);
            this.showError('无法加载页面图片，请重试');
        }
    }
    
    // 显示图片加载状态
    showImageLoading() {
        document.getElementById('modalPageInfo').textContent = '加载中...';
        document.getElementById('imageModal').style.display = 'flex';
    }
    
    // 加载对话历史
    async loadConversations(documentId) {
        try {
            const response = await fetch(`/api/documents/${documentId}/conversations`);
            const data = await response.json();
            
            if (data.success && data.conversations.length > 0) {
                // 清空现有消息
                document.getElementById('chatMessages').innerHTML = '';
                
                // 添加历史对话
                data.conversations.forEach(conv => {
                    this.addMessage(conv.question, 'user');
                    this.addMessage(conv.answer, 'assistant', false, conv.source_pages);
                });
            }
        } catch (error) {
            console.error('加载对话历史失败:', error);
        }
    }
    
    // 添加欢迎消息
    addWelcomeMessage() {
        setTimeout(() => {
            this.addMessage(
                '👋 欢迎使用PDF文档解读智能体！\n\n请上传一个PDF文件，我将帮您：\n• 📝 生成文档总结\n• 💬 回答关于文档的问题\n• 🔍 定位相关页面内容\n\n支持的文件格式：PDF（最大50MB）',
                'assistant'
            );
        }, 500);
    }
    
    // 工具函数
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'error');
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '6px',
            color: 'white',
            fontSize: '14px',
            zIndex: '10000',
            maxWidth: '300px'
        });
        
        const colors = {
            success: '#48bb78',
            error: '#f56565',
            info: '#4299e1',
            warning: '#ed8936'
        };
        toast.style.backgroundColor = colors[type] || colors.info;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 3000);
    }
}

// 初始化应用
const app = new PDFReaderApp();