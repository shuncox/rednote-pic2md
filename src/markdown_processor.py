"""
Markdown处理模块
负责处理OCR结果并生成格式化的Markdown文档
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class PageContent:
    """页面内容数据类"""
    page_number: int
    raw_text: str
    cleaned_text: str
    paragraphs: List[str]


class MarkdownProcessor:
    """Markdown处理器"""
    
    def __init__(self):
        # 常见的段落结束模式
        self.paragraph_end_patterns = [
            r'[。！？]\s*$',  # 中文句号、感叹号、问号
            r'\.\s*$',       # 英文句号
            r'[：:]\s*$',    # 冒号
            r'[；;]\s*$',    # 分号
        ]
        
        # 常见的段落开始模式
        self.paragraph_start_patterns = [
            r'^\s*[（(]\d+[）)]\s*',  # (1) (2) 等
            r'^\s*\d+[\.、]\s*',        # 1. 2、 等
            r'^\s*[一二三四五六七八九十]+[、\.]\s*',  # 一、二、 等
            r'^\s*[•·]\s*',             # 项目符号
            r'^\s*[-*]\s*',             # 破折号和星号
        ]
        
    def clean_ocr_text(self, raw_text: str) -> str:
        """
        清理OCR识别的原始文本
        
        Args:
            raw_text: OCR识别的原始文本
            
        Returns:
            清理后的文本
        """
        if not raw_text:
            return ""
            
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', raw_text.strip())
        
        # 修复常见的OCR错误
        text = self.fix_common_ocr_errors(text)
        
        # 移除行首行尾的空白
        text = text.strip()
        
        return text
        
    def fix_common_ocr_errors(self, text: str) -> str:
        """
        修复常见的OCR识别错误
        
        Args:
            text: 原始文本
            
        Returns:
            修复后的文本
        """
        # 修复常见的标点符号错误
        fixes = [
            (r'，\s*，', '，'),           # 重复的逗号
            (r'。\s*。', '。'),           # 重复的句号
            (r'！\s*！', '！'),           # 重复的感叹号
            (r'？\s*？', '？'),           # 重复的问号
            (r'；\s*；', '；'),           # 重复的分号
            (r'：\s*：', '：'),           # 重复的冒号
            (r'\s+，', '，'),             # 逗号前的空格
            (r'\s*。', '。'),             # 句号前的空格
            (r'\s*！', '！'),             # 感叹号前的空格
            (r'\s*？', '？'),             # 问号前的空格
            (r'\s*；', '；'),             # 分号前的空格
            (r'\s*：', '：'),             # 冒号前的空格
            (r'([，。！？；：])\s+([，。！？；：])', r'\1\2'),  # 标点符号间的空格
        ]
        
        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text)
            
        # 修复常见的字符识别错误
        char_fixes = [
            ('0', 'O', 'O'),  # 数字0和字母O的混淆
            ('1', 'l', 'l'),  # 数字1和字母l的混淆
        ]
        
        # 这里可以根据实际需要添加更多的字符修复规则
        
        return text
        
    def split_into_paragraphs(self, text: str) -> List[str]:
        """
        将文本分割成段落
        
        Args:
            text: 输入文本
            
        Returns:
            段落列表
        """
        if not text:
            return []
            
        # 按换行符分割
        lines = text.split('\n')
        
        paragraphs = []
        current_paragraph = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                # 空行表示段落结束
                if current_paragraph:
                    paragraphs.append(current_paragraph.strip())
                    current_paragraph = ""
                continue
                
            # 检查是否是新段落的开始
            is_new_paragraph = False
            for pattern in self.paragraph_start_patterns:
                if re.match(pattern, line):
                    is_new_paragraph = True
                    break
                    
            if is_new_paragraph and current_paragraph:
                # 开始新段落，保存当前段落
                paragraphs.append(current_paragraph.strip())
                current_paragraph = line
            else:
                # 继续当前段落
                if current_paragraph:
                    current_paragraph += " " + line
                else:
                    current_paragraph = line
                    
        # 添加最后一个段落
        if current_paragraph:
            paragraphs.append(current_paragraph.strip())
            
        return [p for p in paragraphs if p]
        
    def process_page_content(self, page_number: int, raw_text: str) -> PageContent:
        """
        处理单个页面的内容
        
        Args:
            page_number: 页码
            raw_text: OCR识别的原始文本
            
        Returns:
            处理后的页面内容
        """
        cleaned_text = self.clean_ocr_text(raw_text)
        paragraphs = self.split_into_paragraphs(cleaned_text)
        
        return PageContent(
            page_number=page_number,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            paragraphs=paragraphs
        )
        
    def connect_paragraphs_between_pages(self, pages: List[PageContent]) -> List[str]:
        """
        连接页面之间的段落
        
        Args:
            pages: 页面内容列表
            
        Returns:
            连接后的段落列表
        """
        if not pages:
            return []
            
        all_paragraphs = []
        
        for i, page in enumerate(pages):
            if not page.paragraphs:
                continue
                
            # 为每一页添加分页标记（除了第一页）
            if i > 0:
                all_paragraphs.append(f"\n--- 第 {page.page_number} 页 ---\n")
            
            # 添加当前页面的所有段落
            all_paragraphs.extend(page.paragraphs)
                
        return all_paragraphs
        
    def should_connect_paragraphs(self, prev_paragraph: str, next_paragraph: str) -> bool:
        """
        判断两个段落是否应该连接
        
        Args:
            prev_paragraph: 前一个段落
            next_paragraph: 后一个段落
            
        Returns:
            是否应该连接
        """
        if not prev_paragraph or not next_paragraph:
            return False
            
        # 检查前一段落是否以不完整的句子结束
        prev_end = prev_paragraph.strip()
        next_start = next_paragraph.strip()
        
        # 如果前一段落以句号、感叹号、问号等结束，通常不连接
        for pattern in self.paragraph_end_patterns:
            if re.search(pattern, prev_end):
                return False
                
        # 如果后一段落以列表项开始，通常不连接
        for pattern in self.paragraph_start_patterns:
            if re.match(pattern, next_start):
                return False
                
        # 其他情况可以考虑连接
        return True
        
    def generate_markdown(self, pages: List[PageContent], title: str = "", author: str = "") -> str:
        """
        生成Markdown文档
        
        Args:
            pages: 页面内容列表
            title: 文档标题
            author: 作者
            
        Returns:
            Markdown格式的文档
        """
        if not pages:
            return ""
            
        markdown_lines = []
        
        # 添加标题
        if title:
            markdown_lines.append(f"# {title}\n")
            
        # 添加作者信息
        if author:
            markdown_lines.append(f"**作者**: {author}\n")
            
        # 添加分隔线
        markdown_lines.append("---\n")
        
        # 连接段落
        connected_paragraphs = self.connect_paragraphs_between_pages(pages)
        
        # 添加段落内容
        for paragraph in connected_paragraphs:
            if paragraph.startswith("--- 第"):
                # 分页标记
                markdown_lines.append(paragraph)
                markdown_lines.append("")
            else:
                # 普通段落
                markdown_lines.append(paragraph)
                markdown_lines.append("")
                
        # 添加文档结束标记
        markdown_lines.append("---")
        markdown_lines.append("")
        markdown_lines.append("*本文档由小红书图片转Markdown工具自动生成*")
        
        return "\n".join(markdown_lines)
        
    def format_markdown_structure(self, markdown_text: str) -> str:
        """
        格式化Markdown文档结构
        
        Args:
            markdown_text: 原始Markdown文本
            
        Returns:
            格式化后的Markdown文本
        """
        if not markdown_text:
            return ""
            
        lines = markdown_text.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped_line = line.strip()
            
            # 跳过空行
            if not stripped_line:
                # 避免连续多个空行
                if formatted_lines and formatted_lines[-1] != "":
                    formatted_lines.append("")
                continue
            
            # 处理标题
            if stripped_line.startswith('#'):
                formatted_lines.append(stripped_line)
                formatted_lines.append("")  # 标题后添加空行
            # 处理分页标记
            elif stripped_line.startswith("--- 第"):
                formatted_lines.append("")
                formatted_lines.append(stripped_line)
                formatted_lines.append("")
            # 处理分隔线
            elif stripped_line == "---":
                formatted_lines.append(stripped_line)
                formatted_lines.append("")
            # 处理普通段落
            else:
                # 智能换行处理
                formatted_paragraph = self._format_paragraph(stripped_line)
                formatted_lines.extend(formatted_paragraph)
                formatted_lines.append("")  # 段落后添加空行
                    
        # 移除末尾多余的空行
        while formatted_lines and formatted_lines[-1] == "":
            formatted_lines.pop()
            
        return "\n".join(formatted_lines)
        
    def _format_paragraph(self, paragraph: str) -> List[str]:
        """
        格式化单个段落
        
        Args:
            paragraph: 段落文本
            
        Returns:
            格式化后的行列表
        """
        if not paragraph:
            return []
            
        # 如果段落不太长，直接返回
        if len(paragraph) <= 80:
            return [paragraph]
            
        # 智能分割长段落
        lines = []
        current_line = ""
        
        # 按标点符号分割
        sentences = self._split_sentences(paragraph)
        
        for sentence in sentences:
            # 如果当前行为空，直接添加句子
            if not current_line:
                current_line = sentence
            # 如果添加句子后不超过长度限制，追加到当前行
            elif len(current_line + sentence) <= 80:
                current_line += sentence
            # 否则，保存当前行，开始新行
            else:
                if current_line:
                    lines.append(current_line)
                current_line = sentence
                
        # 添加最后一行
        if current_line:
            lines.append(current_line)
            
        return lines
        
    def _split_sentences(self, text: str) -> List[str]:
        """
        按句子分割文本
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        import re
        
        # 定义句子结束标点
        sentence_endings = r'[。！？；]'
        
        # 分割句子
        sentences = re.split(f'({sentence_endings})', text)
        
        # 重新组合句子和标点
        result = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                if sentence.strip():
                    result.append(sentence)
            elif sentences[i].strip():
                # 处理没有标点结尾的最后部分
                result.append(sentences[i])
                
        return result


def main():
    """测试函数"""
    processor = MarkdownProcessor()
    
    # 测试文本清理
    raw_text = "这 是 一 个   测试  文本 。  有 多余 的   空格 。"
    cleaned = processor.clean_ocr_text(raw_text)
    print(f"清理前: {raw_text}")
    print(f"清理后: {cleaned}")
    
    # 测试段落分割
    test_text = """这是第一段。包含多个句子。
    
    这是第二段。
    
    1. 这是列表项1
    2. 这是列表项2
    
    这是第三段。"""
    
    paragraphs = processor.split_into_paragraphs(test_text)
    print(f"\n分割的段落:")
    for i, p in enumerate(paragraphs, 1):
        print(f"{i}. {p}")
    
    # 测试Markdown生成
    pages = [
        processor.process_page_content(1, "这是第一页的内容。包含一些测试文字。"),
        processor.process_page_content(2, "这是第二页的内容。继续测试文字。"),
    ]
    
    markdown = processor.generate_markdown(pages, "测试文档", "测试作者")
    print(f"\n生成的Markdown:\n{markdown}")


if __name__ == "__main__":
    main()
