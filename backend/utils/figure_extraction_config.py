# -*- coding: utf-8 -*-
"""
图表截取优化配置文件

本文件包含了图表定位与截取算法的各种优化参数和配置选项。
这些参数经过精心调优，旨在解决截取不完整、位置偏离等问题。
"""

class FigureExtractionConfig:
    """图表截取优化配置类"""
    
    # 边界扩展配置
    BOUNDARY_EXPANSION = {
        'expansion_ratio': 0.02,  # 向外扩展2%
        'min_margin': 5,          # 最小边距（像素）
        'max_expansion': 0.05     # 最大扩展比例
    }
    
    # 坐标验证配置
    COORDINATE_VALIDATION = {
        'max_coordinate': 0.95,   # 最大坐标值（留出边界空间）
        'min_dimension': 0.08,    # 最小尺寸（8%页面大小）
        'max_dimension': 0.9,     # 最大尺寸（90%页面大小）
        'small_region_threshold': 0.15  # 小区域阈值
    }
    
    # Figure特定调整配置
    FIGURE_ADJUSTMENTS = {
        'title_margin': 0.03,     # Figure标题预留空间（3%）
        'image_margin': 0.01,     # 彩色图片上边界预留空间（1%）
        'height_threshold': 0.25, # 高度阈值，低于此值需要扩展
        'top_offset_threshold': 0.02  # 顶部偏移阈值
    }
    
    # 质量评估配置
    QUALITY_ASSESSMENT = {
        'confidence_weights': {
            'confidence': 0.6,        # 置信度权重
            'boundary_quality': 0.3,  # 边界质量权重
            'completeness': 0.1       # 完整性权重
        },
        'quality_scores': {
            'excellent': 1.0,
            'good': 0.8,
            'fair': 0.6,
            'poor': 0.3
        },
        'thresholds': {
            'with_query': 0.55,       # 有特定查询时的阈值
            'without_query': 0.65,    # 无特定查询时的阈值
            'min_confidence': 0.5     # 最低置信度要求
        }
    }
    
    # 截取质量配置
    EXTRACTION_QUALITY = {
        'min_size_pixels': 80,    # 最小截取尺寸（像素）
        'max_size_ratio': 0.9,    # 最大截取比例
        'png_quality': 98,        # PNG保存质量
        'optimize': True          # 是否优化保存
    }
    
    # Prompt优化配置
    PROMPT_OPTIMIZATION = {
        'temperature': 0.1,       # 低温度确保结果稳定
        'max_tokens': 3000,       # 最大token数
        'enable_boundary_rules': True,     # 启用边界规则
        'enable_completeness_check': True, # 启用完整性检查
        'enable_quality_assessment': True  # 启用质量评估
    }
    
    @classmethod
    def get_expansion_params(cls):
        """获取边界扩展参数"""
        return cls.BOUNDARY_EXPANSION
    
    @classmethod
    def get_validation_params(cls):
        """获取坐标验证参数"""
        return cls.COORDINATE_VALIDATION
    
    @classmethod
    def get_figure_adjustment_params(cls):
        """获取Figure调整参数"""
        return cls.FIGURE_ADJUSTMENTS
    
    @classmethod
    def get_quality_params(cls):
        """获取质量评估参数"""
        return cls.QUALITY_ASSESSMENT
    
    @classmethod
    def get_extraction_params(cls):
        """获取截取质量参数"""
        return cls.EXTRACTION_QUALITY
    
    @classmethod
    def get_prompt_params(cls):
        """获取Prompt优化参数"""
        return cls.PROMPT_OPTIMIZATION

# 全局配置实例
figure_config = FigureExtractionConfig()