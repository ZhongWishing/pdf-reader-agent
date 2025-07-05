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
        this.addWelcomeMessage();
        this.enableChatInput(); // 启用聊天功能
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
                        // 处理完成，立即隐藏上传进度条
                        this.hideUploadProgress();
                        this.showSuccess('PDF处理完成！');
                        
                        // 更新当前文档
                        this.currentDocument = { 
                            id: progress.document_id,
                            filename: progress.filename || '文档',
                            total_pages: progress.total_pages || 0,
                            file_size: progress.file_size || 0
                        };
                        
                        // 显示文档信息
                        this.renderDocumentInfo(this.currentDocument);
                        
                        // 启用聊天输入
                        this.enableChatInput();
                        
                        // 直接显示文档总结消息
                        this.showDocumentSummaryInChat(progress.document_id);
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
            console.log(`开始加载文档: ${documentId}`);
            
            // 显示加载状态
            this.showDocumentLoading();
            
            // 更新当前文档
            this.currentDocument = { id: documentId };
            
            // 获取文档信息
            console.log('正在获取文档信息...');
            const docResponse = await fetch(`/api/documents/${documentId}`);
            
            if (!docResponse.ok) {
                throw new Error(`HTTP ${docResponse.status}: ${docResponse.statusText}`);
            }
            
            const docData = await docResponse.json();
            console.log('文档信息获取成功:', docData);
            
            if (docData.success && docData.document) {
                this.currentDocument = docData.document;
                this.renderDocumentInfo(docData.document);
                
                // 高亮当前文档
                this.highlightCurrentDocument(documentId);
                
                // 启用聊天输入
                this.enableChatInput();
                
                console.log('开始加载对话历史...');
                
                // 只加载对话历史，延迟总结生成
                try {
                    await this.loadConversations(documentId);
                    console.log('对话历史加载完成');
                } catch (error) {
                    console.error('对话历史加载失败:', error);
                }
                
                // 显示总结生成按钮而不是自动生成总结
                this.showSummaryButton(documentId);
                
                console.log('文档加载完成，隐藏加载状态');
                this.hideDocumentLoading();
                this.showSuccess('文档加载成功');
            } else {
                throw new Error(docData.error || '文档数据无效');
            }
        } catch (error) {
            console.error('加载文档失败:', error);
            this.hideDocumentLoading();
            this.showError(`文档加载失败: ${error.message}`);
            
            // 重置状态
            this.currentDocument = null;
            this.disableChatInput();
        }
    }
    
    // 渲染文档信息
    renderDocumentInfo(doc) {
        const documentInfo = document.getElementById('documentInfo');
        const docTitle = document.getElementById('docTitle');
        const docPages = document.getElementById('docPages');
        const docSize = document.getElementById('docSize');
        
        docTitle.textContent = doc.filename;
        docPages.textContent = `${doc.total_pages}页`;
        docSize.textContent = this.formatFileSize(doc.file_size);
        
        documentInfo.style.display = 'block';
    }
    
    // 显示总结生成按钮
    showSummaryButton(documentId) {
        const summaryContent = document.getElementById('summaryContent');
        summaryContent.innerHTML = `
            <div class="summary-placeholder">
                <p>📄 点击下方按钮生成文档智能总结</p>
                <button class="generate-summary-btn" onclick="app.generateDocumentSummary('${documentId}')">
                    🤖 生成智能总结
                </button>
            </div>
        `;
    }
    
    // 生成文档总结
    async generateDocumentSummary(documentId) {
        const summaryContent = document.getElementById('summaryContent');
        const generateBtn = summaryContent.querySelector('.generate-summary-btn');
        
        // 禁用按钮并显示加载状态
        if (generateBtn) {
            generateBtn.disabled = true;
            generateBtn.textContent = '🔄 正在生成总结...';
        }
        
        summaryContent.innerHTML = '<div class="loading-summary">🤖 正在分析文档内容，生成智能总结...</div>';
        
        try {
            await this.loadDocumentSummary(documentId);
        } catch (error) {
            console.error('总结生成失败:', error);
            this.showSummaryButton(documentId);
        }
    }
    
    // 加载文档总结
    async loadDocumentSummary(documentId) {
        const summaryContent = document.getElementById('summaryContent');
        summaryContent.innerHTML = '<div class="loading-summary">正在生成总结...</div>';
        
        try {
            console.log(`开始加载文档总结: ${documentId}`);
            
            // 创建带超时的fetch请求
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                controller.abort();
            }, 60000); // 60秒超时
            
            const response = await fetch(`/api/documents/${documentId}/summary`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            console.log(`总结API响应状态: ${response.status}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('总结API响应数据:', data);
            
            if (data.success) {
                // 添加欢迎消息
                this.addWelcomeMessage(data.summary);
                console.log('总结加载成功，已添加欢迎消息');
                
                // 删除doc-summary元素，避免转圈渲染状态
                const docSummary = document.getElementById('docSummary');
                if (docSummary) {
                    docSummary.remove();
                }
                
                if (data.cached) {
                    console.log('使用缓存的总结');
                } else {
                    console.log('生成新的总结');
                }
            } else {
                console.error('总结生成失败:', data.error);
                summaryContent.innerHTML = `<div class="error-summary">总结生成失败: ${data.error}</div>`;
                
                // 即使总结失败，也要添加基本的欢迎消息
                this.addWelcomeMessage('文档已加载完成，您可以开始提问了。');
                console.log('总结失败，已添加默认欢迎消息');
            }
        } catch (error) {
            console.error('加载总结失败:', error);
            
            let errorMessage = '总结加载失败';
            if (error.name === 'AbortError') {
                errorMessage = '总结生成超时，请稍后重试';
            } else {
                errorMessage = `总结加载失败: ${error.message}`;
            }
            
            summaryContent.innerHTML = `<div class="error-summary">${errorMessage}</div>`;
            
            // 即使总结失败，也要添加基本的欢迎消息
            this.addWelcomeMessage('文档已加载完成，您可以开始提问了。');
            console.log('总结异常，已添加默认欢迎消息');
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
        
        if (this.currentDocument) {
            chatInput.placeholder = '请输入您关于文档的问题...';
        } else {
            chatInput.placeholder = '请输入您的问题（可以上传PDF文档进行文档分析）...';
        }
    }
    
    // 发送消息
    async sendMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();
        
        if (!message || this.isProcessing) return;
        
        this.isProcessing = true;
        this.updateSendButton(false);
        
        // 添加用户消息
        this.addMessage(message, 'user');
        chatInput.value = '';
        
        // 添加加载消息
        const loadingId = this.addMessage('正在分析您的问题...', 'assistant', true);
        
        try {
            const requestBody = {
                question: message
            };
            
            // 如果有当前文档，添加document_id
            if (this.currentDocument && this.currentDocument.id) {
                requestBody.document_id = this.currentDocument.id;
            }
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            const data = await response.json();
            
            // 移除加载消息
            this.removeMessage(loadingId);
            
            if (data.success) {
                // 支持新的混合输出格式
                const answerContent = data.answer_content || data.answer;
                const answerType = data.answer_type || 'text';
                const confidence = data.confidence;
                const pageImages = data.page_images || [];
                const extractedFigures = data.extracted_figures || [];
                const autoExtractedFigures = data.auto_extracted_figures || [];
                
                // 合并手动和自动提取的Figure
                const allExtractedFigures = [...extractedFigures, ...autoExtractedFigures];
                
                this.addMessage(
                    answerContent, 
                    'assistant', 
                    false, 
                    data.source_pages || data.relevant_pages,
                    'normal',
                    answerType,
                    pageImages,
                    confidence,
                    allExtractedFigures
                );
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
    addMessage(content, type, isLoading = false, sourcePages = null, messageType = 'normal', answerType = 'text', pageImages = [], confidence = null, extractedFigures = []) {
        const chatMessages = document.getElementById('chatMessages');
        const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type} ${messageType}`;
        messageDiv.id = messageId;
        
        // 处理页面图片显示
        let pageImagesHtml = '';
        if (pageImages && pageImages.length > 0 && (answerType === 'mixed' || answerType === 'visual')) {
            pageImagesHtml = '<div class="page-images">📷 相关页面截图：';
            pageImages.forEach((imagePath, index) => {
                const pageNumber = this.extractPageNumberFromPath(imagePath);
                pageImagesHtml += `
                    <div class="page-image-container">
                        <img src="${imagePath}" alt="第${pageNumber}页" class="page-image" 
                             onclick="app.showPageImageFromPath('${imagePath}', ${pageNumber})" />
                        <div class="page-image-label">第${pageNumber}页</div>
                    </div>
                `;
            });
            pageImagesHtml += '</div>';
        }
        
        // 处理自动提取的图片显示
        let extractedFiguresHtml = '';
        if (extractedFigures && extractedFigures.length > 0) {
            extractedFiguresHtml = '<div class="extracted-figures">🤖 <strong>系统自动提取的相关图表：</strong>';
            extractedFigures.forEach((figure, index) => {
                const pageNumber = figure.page_number;
                const figureType = figure.type || 'figure';
                // 兼容后端返回的不同字段名
                const imageUrl = figure.image_url || figure.figure_url;
                const description = figure.description || '';
                const analysis = figure.analysis || '';
                
                extractedFiguresHtml += `
                    <div class="extracted-figure-item">
                        <div class="figure-header">
                            <span class="figure-title">📊 ${figureType} ${index + 1} (第${pageNumber}页)</span>
                            ${description ? `<span class="figure-description">${description}</span>` : ''}
                        </div>
                        <div class="figure-image-container">
                            <img src="${imageUrl}" alt="第${pageNumber}页图表" class="extracted-figure-image" 
                                 onclick="app.showExtractedFigure('${imageUrl}', '${figureType} ${index + 1}')" />
                            <div class="figure-overlay">
                                <button class="view-full-btn" onclick="app.showExtractedFigure('${imageUrl}', '${figureType} ${index + 1}')">
                                    🔍 查看完整图片
                                </button>
                            </div>
                        </div>
                        ${analysis ? `<div class="figure-analysis"><strong>图表分析：</strong>${analysis.substring(0, 200)}${analysis.length > 200 ? '...' : ''}</div>` : ''}
                    </div>
                `;
            });
            extractedFiguresHtml += '</div>';
        }
        
        // 处理来源页面链接
        let sourceHtml = '';
        if (sourcePages && sourcePages.length > 0) {
            sourceHtml = '<div class="source-pages">📄 来源页面: ';
            sourcePages.forEach(page => {
                sourceHtml += `<span class="source-page" onclick="app.showPageImage('${this.currentDocument.id}', ${page})">第${page}页</span> `;
            });
            sourceHtml += '</div>';
        }
        
        // 处理置信度显示
        let confidenceHtml = '';
        if (confidence !== null && confidence !== undefined && type === 'assistant') {
            const confidenceLevel = confidence >= 0.8 ? '高' : confidence >= 0.6 ? '中' : '低';
            const confidenceColor = confidence >= 0.8 ? '#48bb78' : confidence >= 0.6 ? '#ed8936' : '#f56565';
            confidenceHtml = `<div class="confidence-indicator" style="color: ${confidenceColor}">🎯 置信度: ${confidenceLevel} (${Math.round(confidence * 100)}%)</div>`;
        }
        
        const timestamp = new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // 格式化内容（支持数学公式和代码块）
        const formattedContent = this.formatMessageContent(content, answerType);
        
        messageDiv.innerHTML = `
            <div class="message-content ${isLoading ? 'loading' : ''}">
                ${formattedContent}
                ${extractedFiguresHtml}
                ${pageImagesHtml}
                ${sourceHtml}
                ${confidenceHtml}
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
                
                const modalImage = document.getElementById('modalImage');
                modalImage.src = imageUrl;
                
                document.getElementById('modalPageInfo').innerHTML = `
                    <strong>第${pageNumber}页</strong>
                    <button id="extractFigureBtn" class="extract-figure-btn" onclick="app.enableFigureExtraction('${documentId}', ${pageNumber})">
                        📷 截取Figure
                    </button>
                `;
                
                document.getElementById('imageModal').style.display = 'flex';
                
                // 存储当前图片信息
                this.currentImageInfo = {
                    documentId: documentId,
                    pageNumber: pageNumber,
                    imageUrl: imageUrl
                };
                
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
    
    // 显示截取的Figure图片
    showExtractedFigure(imageUrl, figureTitle) {
        try {
            const modalImage = document.getElementById('modalImage');
            modalImage.src = imageUrl;
            
            document.getElementById('modalPageInfo').innerHTML = `
                <strong>${figureTitle}</strong>
                <span style="color: #666; font-size: 0.9em;">（系统自动截取的图表）</span>
            `;
            
            document.getElementById('imageModal').style.display = 'flex';
            
            // 存储当前图片信息
            this.currentImageInfo = {
                imageUrl: imageUrl,
                figureTitle: figureTitle
            };
        } catch (error) {
            console.error('显示截取图片失败:', error);
            this.showError('无法显示图片，请重试');
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
            console.log(`开始加载对话历史: ${documentId}`);
            
            const response = await fetch(`/api/documents/${documentId}/conversations`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('对话历史API响应:', data);
            
            if (data.success) {
                if (data.conversations && data.conversations.length > 0) {
                    console.log(`找到 ${data.conversations.length} 条历史对话`);
                    
                    // 清空现有消息（但不清空欢迎消息）
                    const chatMessages = document.getElementById('chatMessages');
                    const existingMessages = chatMessages.querySelectorAll('.message');
                    existingMessages.forEach(msg => {
                        if (!msg.textContent.includes('文档总结') && !msg.textContent.includes('欢迎使用')) {
                            msg.remove();
                        }
                    });
                    
                    // 添加历史对话
                    data.conversations.forEach(conv => {
                        this.addMessage(conv.question, 'user');
                        this.addMessage(conv.answer, 'assistant', false, conv.source_pages);
                    });
                    
                    console.log('对话历史加载完成');
                } else {
                    console.log('没有找到历史对话');
                }
            } else {
                console.warn('对话历史加载失败:', data.error);
            }
        } catch (error) {
            console.error('加载对话历史失败:', error);
            // 对话历史加载失败不应该阻塞整个文档加载流程
        }
    }
    
    // 在聊天框中显示文档总结
    async showDocumentSummaryInChat(documentId) {
        try {
            console.log(`开始获取文档总结并显示在聊天框: ${documentId}`);
            
            // 清空现有消息
            document.getElementById('chatMessages').innerHTML = '';
            
            // 添加加载消息
            const loadingId = this.addMessage('🤖 正在生成文档总结，请稍候...', 'assistant', true);
            
            const response = await fetch(`/api/documents/${documentId}/summary`);
            const data = await response.json();
            
            // 移除加载消息
            this.removeMessage(loadingId);
            
            if (data.success && data.summary) {
                // 在聊天框中添加总结消息
                this.addMessage(
                    `📄 **文档总结**\n\n${data.summary}\n\n---\n\n💬 您可以基于此文档内容向我提问，我将为您提供详细的解答和页面定位。`, 
                    'assistant', 
                    false, 
                    null, 
                    'summary'
                );
                console.log('文档总结已显示在聊天框中');
            } else {
                console.error('获取文档总结失败:', data.error);
                this.addMessage(
                    '📄 文档已处理完成，但总结生成失败。您可以开始提问了。', 
                    'assistant', 
                    false, 
                    null, 
                    'info'
                );
            }
        } catch (error) {
            console.error('显示文档总结失败:', error);
            this.addMessage(
                '📄 文档已处理完成，您可以开始提问了。', 
                'assistant', 
                false, 
                null, 
                'info'
            );
        }
    }

    // 添加欢迎消息
    addWelcomeMessage(summary = null) {
        // 清空现有消息
        document.getElementById('chatMessages').innerHTML = '';
        
        setTimeout(() => {
            if (summary) {
                // 如果有总结，显示总结内容
                this.addMessage(
                    `📄 **文档总结**\n\n${summary}\n\n---\n\n💬 您可以基于此文档内容向我提问，我将为您提供详细的解答和页面定位。`,
                    'assistant',
                    false,
                    null,
                    'normal',
                    'mixed'
                );
            } else {
                // 默认欢迎消息
                this.addMessage(
                    '👋 欢迎使用PDF文档解读智能体！\n\n🤖 **您可以直接开始对话**，我可以回答各种问题。\n\n📄 **上传PDF文档后**，我还能帮您：\n• 📝 生成文档总结\n• 💬 回答关于文档的问题\n• 🔍 定位相关页面内容\n• 📊 自动提取图表和表格\n\n支持的文件格式：PDF（最大50MB）',
                    'assistant'
                );
            }
        }, 500);
    }
    
    // 从图片路径中提取页码
    extractPageNumberFromPath(imagePath) {
        const match = imagePath.match(/page_(\d+)/);
        return match ? parseInt(match[1]) : 1;
    }
    
    // 显示指定路径的页面图片
    async showPageImageFromPath(imagePath, pageNumber) {
        try {
            document.getElementById('modalImage').src = imagePath;
            document.getElementById('modalPageInfo').innerHTML = `
                <strong>第${pageNumber}页</strong>
            `;
            document.getElementById('imageModal').style.display = 'flex';
        } catch (error) {
            console.error('显示页面图片失败:', error);
            this.showError('无法显示页面图片');
        }
    }
    
    // 启用Figure截取模式
    enableFigureExtraction(documentId, pageNumber) {
        const modalImage = document.getElementById('modalImage');
        const modal = document.getElementById('imageModal');
        
        // 创建选择框覆盖层
        const selectionOverlay = document.createElement('div');
        selectionOverlay.id = 'selectionOverlay';
        selectionOverlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            cursor: crosshair;
            z-index: 1000;
        `;
        
        // 添加到模态框
        modal.appendChild(selectionOverlay);
        
        // 更新按钮状态
        document.getElementById('modalPageInfo').innerHTML = `
            <strong>第${pageNumber}页</strong>
            <div class="extraction-controls">
                <span class="extraction-hint">🖱️ 拖拽选择要截取的区域</span>
                <button onclick="app.cancelFigureExtraction()" class="cancel-btn">取消</button>
            </div>
        `;
        
        // 添加选择功能
        this.setupImageSelection(selectionOverlay, documentId, pageNumber);
    }
    
    // 设置图片选择功能
    setupImageSelection(overlay, documentId, pageNumber) {
        let isSelecting = false;
        let startX, startY, selectionBox;
        
        overlay.addEventListener('mousedown', (e) => {
            isSelecting = true;
            const rect = overlay.getBoundingClientRect();
            startX = e.clientX - rect.left;
            startY = e.clientY - rect.top;
            
            // 创建选择框
            selectionBox = document.createElement('div');
            selectionBox.style.cssText = `
                position: absolute;
                border: 2px dashed #007bff;
                background: rgba(0, 123, 255, 0.1);
                pointer-events: none;
                left: ${startX}px;
                top: ${startY}px;
                width: 0;
                height: 0;
            `;
            overlay.appendChild(selectionBox);
        });
        
        overlay.addEventListener('mousemove', (e) => {
            if (!isSelecting || !selectionBox) return;
            
            const rect = overlay.getBoundingClientRect();
            const currentX = e.clientX - rect.left;
            const currentY = e.clientY - rect.top;
            
            const width = Math.abs(currentX - startX);
            const height = Math.abs(currentY - startY);
            const left = Math.min(currentX, startX);
            const top = Math.min(currentY, startY);
            
            selectionBox.style.left = left + 'px';
            selectionBox.style.top = top + 'px';
            selectionBox.style.width = width + 'px';
            selectionBox.style.height = height + 'px';
        });
        
        overlay.addEventListener('mouseup', (e) => {
            if (!isSelecting || !selectionBox) return;
            
            isSelecting = false;
            
            const rect = overlay.getBoundingClientRect();
            const endX = e.clientX - rect.left;
            const endY = e.clientY - rect.top;
            
            // 计算选择区域的相对坐标（0-1之间）
            const x = Math.min(startX, endX) / rect.width;
            const y = Math.min(startY, endY) / rect.height;
            const width = Math.abs(endX - startX) / rect.width;
            const height = Math.abs(endY - startY) / rect.height;
            
            // 检查选择区域是否有效
            if (width > 0.02 && height > 0.02) {
                this.confirmFigureExtraction(documentId, pageNumber, { x, y, width, height });
            } else {
                this.showError('选择区域太小，请重新选择');
                selectionBox.remove();
            }
        });
    }
    
    // 确认Figure截取
    confirmFigureExtraction(documentId, pageNumber, coordinates) {
        const figureName = prompt('请输入Figure名称（可选）:', `Figure_${pageNumber}`);
        if (figureName === null) {
            this.cancelFigureExtraction();
            return;
        }
        
        this.extractFigure(documentId, pageNumber, coordinates, figureName || `Figure_${pageNumber}`);
    }
    
    // 执行Figure截取
    async extractFigure(documentId, pageNumber, coordinates, figureName) {
        try {
            this.showSuccess('正在截取Figure...');
            
            const response = await fetch(`/api/documents/${documentId}/pages/${pageNumber}/extract_figure`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    x: coordinates.x,
                    y: coordinates.y,
                    width: coordinates.width,
                    height: coordinates.height,
                    figure_name: figureName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('Figure截取成功！');
                
                // 显示截取的图片
                this.showExtractedFigure(data.figure_url, figureName);
                
                // 关闭选择模式
                this.cancelFigureExtraction();
            } else {
                throw new Error(data.error || 'Figure截取失败');
            }
        } catch (error) {
            console.error('Figure截取失败:', error);
            this.showError(`Figure截取失败: ${error.message}`);
        }
    }
    
    // 显示截取的Figure
    showExtractedFigure(figureUrl, figureName) {
        // 创建新的模态框显示截取的图片
        const figureModal = document.createElement('div');
        figureModal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10001;
        `;
        
        figureModal.innerHTML = `
            <div style="background: white; padding: 20px; border-radius: 8px; max-width: 90%; max-height: 90%; overflow: auto;">
                <h3>截取的Figure: ${figureName}</h3>
                <img src="${figureUrl}" style="max-width: 100%; height: auto; border: 1px solid #ddd;" />
                <div style="margin-top: 15px; text-align: center;">
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">关闭</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(figureModal);
        
        // 点击背景关闭
        figureModal.addEventListener('click', (e) => {
            if (e.target === figureModal) {
                figureModal.remove();
            }
        });
    }
    
    // 取消Figure截取
    cancelFigureExtraction() {
        const overlay = document.getElementById('selectionOverlay');
        if (overlay) {
            overlay.remove();
        }
        
        // 恢复原始按钮
        if (this.currentImageInfo) {
            document.getElementById('modalPageInfo').innerHTML = `
                <strong>第${this.currentImageInfo.pageNumber}页</strong>
                <button id="extractFigureBtn" class="extract-figure-btn" onclick="app.enableFigureExtraction('${this.currentImageInfo.documentId}', ${this.currentImageInfo.pageNumber})">
                    📷 截取Figure
                </button>
            `;
        }
    }
    
    // 格式化消息内容
    formatMessageContent(content, answerType = 'text') {
        if (!content) return '';
        
        let formattedContent = content;
        
        // 先处理代码块（避免其他格式化影响代码内容）
        const codeBlocks = [];
        formattedContent = formattedContent.replace(/```([\w]*)?\n?([\s\S]*?)```/g, (match, lang, code) => {
            const index = codeBlocks.length;
            codeBlocks.push(`<pre class="code-block"><code class="language-${lang || 'text'}">${this.escapeHtml(code.trim())}</code></pre>`);
            return `__CODE_BLOCK_${index}__`;
        });
        
        // 处理行内代码
        const inlineCodes = [];
        formattedContent = formattedContent.replace(/`([^`\n]+)`/g, (match, code) => {
            const index = inlineCodes.length;
            inlineCodes.push(`<code class="inline-code">${this.escapeHtml(code)}</code>`);
            return `__INLINE_CODE_${index}__`;
        });
        
        // 处理数学公式（LaTeX格式）
        const mathBlocks = [];
        // 处理 $$...$$
        formattedContent = formattedContent.replace(/\$\$([\s\S]*?)\$\$/g, (match, formula) => {
            const index = mathBlocks.length;
            mathBlocks.push(`<div class="math-block">${this.escapeHtml(formula.trim())}</div>`);
            return `__MATH_BLOCK_${index}__`;
        });
        
        // 处理 \[...\]
        formattedContent = formattedContent.replace(/\\\[([\s\S]*?)\\\]/g, (match, formula) => {
            const index = mathBlocks.length;
            mathBlocks.push(`<div class="math-block">${this.escapeHtml(formula.trim())}</div>`);
            return `__MATH_BLOCK_${index}__`;
        });
        
        const mathInlines = [];
        formattedContent = formattedContent.replace(/\$([^$\n]+)\$/g, (match, formula) => {
            const index = mathInlines.length;
            mathInlines.push(`<span class="math-inline">${this.escapeHtml(formula)}</span>`);
            return `__MATH_INLINE_${index}__`;
        });
        
        // 处理标题（# ## ### #### ##### ######）
        formattedContent = formattedContent.replace(/^(#{1,6})\s+(.+)$/gm, (match, hashes, title) => {
            const level = hashes.length;
            return `<h${level} class="markdown-h${level}">${title.trim()}</h${level}>`;
        });
        
        // 处理无序列表
        formattedContent = formattedContent.replace(/^(\s*)[\*\-\+]\s+(.+)$/gm, (match, indent, item) => {
            const level = Math.floor(indent.length / 2) + 1;
            return `<li class="markdown-li markdown-li-${level}">${item.trim()}</li>`;
        });
        
        // 处理有序列表
        formattedContent = formattedContent.replace(/^(\s*)\d+\.\s+(.+)$/gm, (match, indent, item) => {
            const level = Math.floor(indent.length / 2) + 1;
            return `<li class="markdown-oli markdown-oli-${level}">${item.trim()}</li>`;
        });
        
        // 包装连续的列表项
        formattedContent = formattedContent.replace(/(<li class="markdown-li[^"]*">[^<]*<\/li>\s*)+/g, (match) => {
            return `<ul class="markdown-ul">${match}</ul>`;
        });
        
        formattedContent = formattedContent.replace(/(<li class="markdown-oli[^"]*">[^<]*<\/li>\s*)+/g, (match) => {
            return `<ol class="markdown-ol">${match}</ol>`;
        });
        
        // 处理链接 [text](url)
        formattedContent = formattedContent.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" class="markdown-link" target="_blank" rel="noopener noreferrer">$1</a>');
        
        // 处理图片 ![alt](url)
        formattedContent = formattedContent.replace(/!\[([^\]]*)\]\(([^\)]+)\)/g, '<img src="$2" alt="$1" class="markdown-image" />');
        
        // 处理表格（简单实现）
        formattedContent = formattedContent.replace(/^\|(.+)\|\s*$/gm, (match, content) => {
            const cells = content.split('|').map(cell => cell.trim()).filter(cell => cell);
            const cellsHtml = cells.map(cell => `<td class="markdown-td">${cell}</td>`).join('');
            return `<tr class="markdown-tr">${cellsHtml}</tr>`;
        });
        
        // 包装表格行
        formattedContent = formattedContent.replace(/(<tr class="markdown-tr">[\s\S]*?<\/tr>\s*)+/g, (match) => {
            return `<table class="markdown-table"><tbody>${match}</tbody></table>`;
        });
        
        // 处理引用块
        formattedContent = formattedContent.replace(/^>\s+(.+)$/gm, '<blockquote class="markdown-blockquote">$1</blockquote>');
        
        // 处理水平分割线
        formattedContent = formattedContent.replace(/^(\*{3,}|\-{3,}|_{3,})$/gm, '<hr class="markdown-hr" />');
        
        // 处理粗体和斜体（在其他格式化之后）
        formattedContent = formattedContent.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
        formattedContent = formattedContent.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        formattedContent = formattedContent.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // 处理删除线
        formattedContent = formattedContent.replace(/~~([^~]+)~~/g, '<del class="markdown-del">$1</del>');
        
        // 处理换行符（在所有其他处理之后）
        formattedContent = formattedContent.replace(/\n/g, '<br>');
        
        // 恢复代码块和数学公式
        codeBlocks.forEach((block, index) => {
            formattedContent = formattedContent.replace(`__CODE_BLOCK_${index}__`, block);
        });
        
        inlineCodes.forEach((code, index) => {
            formattedContent = formattedContent.replace(`__INLINE_CODE_${index}__`, code);
        });
        
        mathBlocks.forEach((block, index) => {
            formattedContent = formattedContent.replace(`__MATH_BLOCK_${index}__`, block);
        });
        
        mathInlines.forEach((inline, index) => {
            formattedContent = formattedContent.replace(`__MATH_INLINE_${index}__`, inline);
        });
        
        return formattedContent;
    }
    
    // HTML转义函数
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
    
    showDocumentLoading() {
        const documentInfo = document.getElementById('documentInfo');
        if (documentInfo) {
            documentInfo.style.display = 'block';
            documentInfo.innerHTML = '<div class="loading">正在加载文档...</div>';
        }
    }
    
    hideDocumentLoading() {
        // 加载状态会被renderDocumentInfo覆盖，无需特殊处理
    }
    
    disableChatInput() {
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendButton');
        
        if (chatInput) {
            chatInput.disabled = true;
            chatInput.placeholder = '请先选择一个文档';
        }
        
        if (sendButton) {
            sendButton.disabled = true;
        }
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