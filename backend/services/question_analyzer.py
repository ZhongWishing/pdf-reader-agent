import re
import jieba
from typing import List, Dict, Any, Tuple

class QuestionAnalyzer:
    """问题分析器"""
    
    def __init__(self):
        # 问题类型关键词
        self.summary_keywords = [
            '总结', '概括', '摘要', '主要内容', '大概', '整体', '全文', 
            '主题', '核心', '要点', '梗概', '简述', '介绍一下'
        ]
        
        self.page_keywords = [
            '第', '页', 'page', 'p', '第几页', '哪一页', '哪页'
        ]
        
        self.detail_keywords = [
            '详细', '具体', '细节', '深入', '进一步', '更多', '详情'
        ]
        
        self.data_keywords = [
            '数据', '数字', '统计', '图表', '表格', '图', '表', 
            '百分比', '%', '比例', '数量', '金额', '价格'
        ]
        
        self.comparison_keywords = [
            '比较', '对比', '差异', '区别', '相同', '不同', '异同'
        ]
        
        # Figure和Table相关关键词
        self.figure_keywords = [
            'figure', 'fig', '图', '图片', '图像', '图表', '示意图', 
            '流程图', '结构图', '框图', '图形', '插图', '配图',
            'table', '表', '表格', '数据表', '统计表', '对比表', '列表'
        ]
        
        # 位置关键词
        self.location_keywords = {
            'beginning': ['开头', '开始', '前面', '首先', '第一'],
            'middle': ['中间', '中部', '中央'],
            'end': ['结尾', '结束', '最后', '末尾', '结论']
        }
    
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """分析问题
        
        Args:
            question: 用户问题
            
        Returns:
            分析结果
        """
        question = question.strip()
        
        # 基本分析
        analysis = {
            'original_question': question,
            'question_type': self._detect_question_type(question),
            'keywords': self._extract_keywords(question),
            'page_info': self._extract_page_info(question),
            'location_info': self._extract_location_info(question),
            'complexity': self._analyze_complexity(question),
            'requires_multiple_pages': self._requires_multiple_pages(question),
            'figure_info': self._extract_figure_info(question)
        }
        
        return analysis
    
    def _detect_question_type(self, question: str) -> str:
        """检测问题类型
        
        Args:
            question: 问题文本
            
        Returns:
            问题类型
        """
        question_lower = question.lower()
        
        # 检查是否是总结类问题
        if any(keyword in question for keyword in self.summary_keywords):
            return 'summary'
        
        # 检查是否指定了页码
        if any(keyword in question for keyword in self.page_keywords):
            return 'specific_page'
        
        # 检查是否是数据查询
        if any(keyword in question for keyword in self.data_keywords):
            return 'data_query'
        
        # 检查是否是比较类问题
        if any(keyword in question for keyword in self.comparison_keywords):
            return 'comparison'
        
        # 检查是否需要详细信息
        if any(keyword in question for keyword in self.detail_keywords):
            return 'detail_query'
        
        # 检查是否是Figure查询
        if any(keyword in question_lower for keyword in self.figure_keywords):
            return 'figure_query'
        
        # 默认为内容查询
        return 'content_query'
    
    def _extract_keywords(self, question: str) -> List[str]:
        """提取关键词
        
        Args:
            question: 问题文本
            
        Returns:
            关键词列表
        """
        # 使用jieba分词
        words = jieba.lcut(question)
        
        # 过滤停用词和标点符号
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '什么', '请', '问', '吗', '呢', '吧', '啊', '哦', '嗯',
            '？', '！', '。', '，', '、', '；', '：', '"', "'", '(', ')', '[', ']', '{', '}'
        }
        
        # 过滤关键词
        keywords = []
        for word in words:
            word = word.strip()
            if (len(word) > 1 and 
                word not in stop_words and 
                not word.isdigit() and 
                word.isalnum()):
                keywords.append(word)
        
        return keywords
    
    def _extract_page_info(self, question: str) -> Dict[str, Any]:
        """提取页面信息
        
        Args:
            question: 问题文本
            
        Returns:
            页面信息
        """
        page_info = {
            'has_page_reference': False,
            'page_numbers': [],
            'page_ranges': []
        }
        
        # 匹配具体页码：第X页、第X-Y页、页X等
        page_patterns = [
            r'第(\d+)页',
            r'第(\d+)-(\d+)页',
            r'页(\d+)',
            r'page\s*(\d+)',
            r'p\s*(\d+)'
        ]
        
        for pattern in page_patterns:
            matches = re.finditer(pattern, question, re.IGNORECASE)
            for match in matches:
                page_info['has_page_reference'] = True
                if len(match.groups()) == 1:
                    # 单页
                    page_num = int(match.group(1))
                    page_info['page_numbers'].append(page_num)
                elif len(match.groups()) == 2:
                    # 页面范围
                    start_page = int(match.group(1))
                    end_page = int(match.group(2))
                    page_info['page_ranges'].append((start_page, end_page))
        
        return page_info
    
    def _extract_location_info(self, question: str) -> Dict[str, Any]:
        """提取位置信息
        
        Args:
            question: 问题文本
            
        Returns:
            位置信息
        """
        location_info = {
            'has_location': False,
            'locations': []
        }
        
        for location, keywords in self.location_keywords.items():
            if any(keyword in question for keyword in keywords):
                location_info['has_location'] = True
                location_info['locations'].append(location)
        
        return location_info
    
    def _analyze_complexity(self, question: str) -> str:
        """分析问题复杂度
        
        Args:
            question: 问题文本
            
        Returns:
            复杂度级别
        """
        # 简单问题：单一概念查询
        if len(question) < 10:
            return 'simple'
        
        # 复杂问题：包含多个条件、比较、分析等
        complex_indicators = [
            '为什么', '如何', '怎样', '分析', '评价', '比较', '对比',
            '原因', '影响', '结果', '关系', '趋势', '变化'
        ]
        
        if any(indicator in question for indicator in complex_indicators):
            return 'complex'
        
        # 中等复杂度
        return 'medium'
    
    def _requires_multiple_pages(self, question: str) -> bool:
        """判断是否需要多页面信息
        
        Args:
            question: 问题文本
            
        Returns:
            是否需要多页面
        """
        multiple_page_indicators = [
            '全部', '所有', '整个', '完整', '全文', '总体', '整体',
            '比较', '对比', '关系', '联系', '趋势', '变化', '发展'
        ]
        
        return any(indicator in question for indicator in multiple_page_indicators)
    
    def _extract_figure_info(self, question: str) -> Dict[str, Any]:
        """提取Figure相关信息
        
        Args:
            question: 问题文本
            
        Returns:
            Figure信息
        """
        figure_info = {
            'has_figure_request': False,
            'figure_numbers': [],
            'figure_types': [],
            'figure_descriptions': []
        }
        
        question_lower = question.lower()
        
        # 检查是否包含Figure关键词
        if any(keyword in question_lower for keyword in self.figure_keywords):
            figure_info['has_figure_request'] = True
        
        # 提取Figure和Table编号：Figure 1, Fig. 2, 图1, Table 1, 表1等
        figure_patterns = [
            r'figure\s*(\d+)',
            r'fig\.?\s*(\d+)',
            r'图\s*(\d+)',
            r'图片\s*(\d+)',
            r'图表\s*(\d+)',
            r'table\s*(\d+)',
            r'表\s*(\d+)',
            r'表格\s*(\d+)',
            r'第\s*(\d+)\s*表',
            r'第\s*(\d+)\s*图'
        ]
        
        for pattern in figure_patterns:
            matches = re.finditer(pattern, question_lower)
            for match in matches:
                figure_info['has_figure_request'] = True
                figure_num = int(match.group(1))
                if figure_num not in figure_info['figure_numbers']:
                    figure_info['figure_numbers'].append(figure_num)
        
        # 提取Figure和Table类型描述
        type_patterns = [
            r'(流程图|结构图|框图|示意图|配图|插图)',
            r'(chart|diagram|graph|plot|image)',
            r'(数据表|统计表|对比表|汇总表|列表|表格)',
            r'(table|list|chart)'
        ]
        
        for pattern in type_patterns:
            matches = re.finditer(pattern, question_lower)
            for match in matches:
                figure_type = match.group(1)
                if figure_type not in figure_info['figure_types']:
                    figure_info['figure_types'].append(figure_type)
        
        return figure_info


class PageSelector:
    """页面选择器"""
    
    def __init__(self, pdf_processor):
        self.pdf_processor = pdf_processor
        self.question_analyzer = QuestionAnalyzer()
    
    def select_relevant_pages(self, document_id: str, question: str, 
                            max_pages: int = 3) -> List[int]:
        """选择相关页面
        
        Args:
            document_id: 文档ID
            question: 用户问题
            max_pages: 最大页面数
            
        Returns:
            相关页面号列表
        """
        # 分析问题
        analysis = self.question_analyzer.analyze_question(question)
        
        # 获取文档信息
        doc_info = self.pdf_processor.get_document_info(document_id)
        if not doc_info['success']:
            return []
        
        document = doc_info['document']
        total_pages = document['total_pages']
        
        # 如果是Figure查询，搜索所有页面
        if analysis['figure_info']['has_figure_request']:
            print(f"检测到Figure查询，将搜索所有 {total_pages} 页")
            return list(range(1, total_pages + 1))
        
        # 根据问题类型选择页面
        if analysis['question_type'] == 'summary':
            return self._select_for_summary(total_pages, max_pages)
        
        elif analysis['question_type'] == 'specific_page':
            return self._select_specific_pages(analysis['page_info'], total_pages)
        
        elif analysis['page_info']['has_page_reference']:
            return self._select_specific_pages(analysis['page_info'], total_pages)
        
        else:
            return self._select_by_content_matching(
                document_id, analysis['keywords'], total_pages, max_pages
            )
    
    def _select_for_summary(self, total_pages: int, max_pages: int) -> List[int]:
        """为总结类问题选择页面
        
        Args:
            total_pages: 总页数
            max_pages: 最大页面数
            
        Returns:
            页面号列表
        """
        if total_pages <= max_pages:
            return list(range(1, total_pages + 1))
        
        # 选择开头、中间、结尾的页面
        selected_pages = []
        
        # 开头页面
        selected_pages.append(1)
        if total_pages > 1:
            selected_pages.append(2)
        
        # 中间页面
        if total_pages > 4 and len(selected_pages) < max_pages:
            middle_page = total_pages // 2
            selected_pages.append(middle_page)
        
        # 结尾页面
        if total_pages > 2 and len(selected_pages) < max_pages:
            selected_pages.append(total_pages)
        
        return sorted(list(set(selected_pages)))
    
    def _select_specific_pages(self, page_info: Dict[str, Any], 
                             total_pages: int) -> List[int]:
        """选择指定页面
        
        Args:
            page_info: 页面信息
            total_pages: 总页数
            
        Returns:
            页面号列表
        """
        selected_pages = []
        
        # 添加具体页码
        for page_num in page_info['page_numbers']:
            if 1 <= page_num <= total_pages:
                selected_pages.append(page_num)
        
        # 添加页面范围
        for start_page, end_page in page_info['page_ranges']:
            for page_num in range(start_page, min(end_page + 1, total_pages + 1)):
                if 1 <= page_num <= total_pages:
                    selected_pages.append(page_num)
        
        return sorted(list(set(selected_pages)))
    
    def _select_by_content_matching(self, document_id: str, keywords: List[str], 
                                  total_pages: int, max_pages: int) -> List[int]:
        """基于内容匹配选择页面
        
        Args:
            document_id: 文档ID
            keywords: 关键词列表
            total_pages: 总页数
            max_pages: 最大页面数
            
        Returns:
            页面号列表
        """
        if not keywords:
            # 如果没有关键词，返回默认页面
            return self._get_default_pages(total_pages, max_pages)
        
        # 这里可以实现更复杂的内容匹配逻辑
        # 目前简化为返回前几页
        return self._get_default_pages(total_pages, max_pages)
    
    def _get_default_pages(self, total_pages: int, max_pages: int) -> List[int]:
        """获取默认页面
        
        Args:
            total_pages: 总页数
            max_pages: 最大页面数
            
        Returns:
            页面号列表
        """
        if total_pages <= max_pages:
            return list(range(1, total_pages + 1))
        
        # 返回前几页
        return list(range(1, max_pages + 1))
    
    def get_page_content(self, document_id: str, page_numbers: List[int]) -> List[str]:
        """获取页面内容
        
        Args:
            document_id: 文档ID
            page_numbers: 页面号列表
            
        Returns:
            页面内容列表
        """
        # 这里应该返回已经通过Qwen分析的页面内容
        # 目前返回空列表，实际实现中需要从缓存或重新分析获取
        return []