"""
文件名解析和排序模块
负责解析小红书图片文件名并生成有序的文件列表
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional


class FileParser:
    """文件名解析器"""
    
    def __init__(self):
        # 匹配小红书文件名的正则表达式
        # 示例: 一个很笨但能成功写出SSCI的小tips_2_博士小导师_来自小红书网页版.jpg
        self.pattern = re.compile(r'(.+?)_(\d+)_(.+?)_来自小红书网页版\.(.+)$')
        
    def parse_filename(self, filename: str) -> Optional[Tuple[str, int, str, str]]:
        """
        解析单个文件名
        
        Args:
            filename: 文件名
            
        Returns:
            Tuple[标题, 序号, 作者, 扩展名] 或 None
        """
        match = self.pattern.match(filename)
        if match:
            title, page_num, author, extension = match.groups()
            try:
                page_num = int(page_num)
                return title, page_num, author, extension
            except ValueError:
                return None
        return None
        
    def detect_series_files(self, selected_file: str) -> List[str]:
        """
        根据选中的文件自动检测系列中的其他文件
        
        Args:
            selected_file: 用户选中的文件路径
            
        Returns:
            排序后的文件路径列表
        """
        filename = os.path.basename(selected_file)
        parsed = self.parse_filename(filename)
        
        if not parsed:
            return [selected_file]
            
        title, _, author, extension = parsed
        
        # 获取文件所在目录
        directory = os.path.dirname(selected_file)
        
        # 搜索目录中的所有相关文件
        series_files = []
        
        try:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    file_parsed = self.parse_filename(file)
                    if file_parsed:
                        file_title, _, file_author, file_extension = file_parsed
                        # 检查是否为同一系列
                        if (file_title == title and 
                            file_author == author and 
                            file_extension == extension):
                            series_files.append(file_path)
        except OSError as e:
            print(f"读取目录失败: {e}")
            return [selected_file]
            
        # 按页码排序
        sorted_files = self.sort_files_by_page_number(series_files)
        
        return sorted_files
        
    def sort_files_by_page_number(self, file_paths: List[str]) -> List[str]:
        """
        根据文件名中的页码对文件进行排序
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            排序后的文件路径列表
        """
        def get_page_number(file_path: str) -> int:
            filename = os.path.basename(file_path)
            parsed = self.parse_filename(filename)
            if parsed:
                return parsed[1]  # 返回页码
            return 0
            
        return sorted(file_paths, key=get_page_number)
        
    def get_file_series_info(self, file_paths: List[str]) -> dict:
        """
        获取文件系列信息
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            包含系列信息的字典
        """
        if not file_paths:
            return {}
            
        first_file = file_paths[0]
        filename = os.path.basename(first_file)
        parsed = self.parse_filename(filename)
        
        if not parsed:
            return {}
            
        title, _, author, extension = parsed
        
        return {
            "title": title,
            "author": author,
            "extension": extension,
            "count": len(file_paths),
            "files": file_paths
        }
        
    def validate_file_series(self, file_paths: List[str]) -> Tuple[bool, str]:
        """
        验证文件系列是否完整
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            Tuple[是否完整, 描述信息]
        """
        if not file_paths:
            return False, "没有文件"
            
        # 检查所有文件是否属于同一系列
        first_parsed = None
        page_numbers = []
        
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            parsed = self.parse_filename(filename)
            
            if not parsed:
                return False, f"文件 {filename} 格式不正确"
                
            title, page_num, author, extension = parsed
            
            if first_parsed is None:
                first_parsed = (title, author, extension)
            else:
                if (title != first_parsed[0] or 
                    author != first_parsed[1] or 
                    extension != first_parsed[2]):
                    return False, f"文件 {filename} 不属于同一系列"
                    
            page_numbers.append(page_num)
            
        # 检查页码是否连续
        page_numbers.sort()
        for i in range(1, len(page_numbers)):
            if page_numbers[i] != page_numbers[i-1] + 1:
                return False, f"页码不连续，缺少第 {page_numbers[i-1] + 1} 页"
                
        return True, f"系列完整，共 {len(page_numbers)} 页"
        
    def get_missing_files(self, file_paths: List[str]) -> List[int]:
        """
        获取缺失的页码列表
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            缺失的页码列表
        """
        if not file_paths:
            return []
            
        page_numbers = []
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            parsed = self.parse_filename(filename)
            if parsed:
                page_numbers.append(parsed[1])
                
        if not page_numbers:
            return []
            
        page_numbers.sort()
        missing_pages = []
        
        for i in range(page_numbers[0], page_numbers[-1] + 1):
            if i not in page_numbers:
                missing_pages.append(i)
                
        return missing_pages


def main():
    """测试函数"""
    parser = FileParser()
    
    # 测试文件名解析
    test_filename = "一个很笨但能成功写出SSCI的小tips_2_博士小导师_来自小红书网页版.jpg"
    result = parser.parse_filename(test_filename)
    print(f"解析结果: {result}")
    
    # 测试文件排序
    test_files = [
        "/path/to/一个很笨但能成功写出SSCI的小tips_5_博士小导师_来自小红书网页版.jpg",
        "/path/to/一个很笨但能成功写出SSCI的小tips_2_博士小导师_来自小红书网页版.jpg",
        "/path/to/一个很笨但能成功写出SSCI的小tips_1_博士小导师_来自小红书网页版.jpg",
        "/path/to/一个很笨但能成功写出SSCI的小tips_3_博士小导师_来自小红书网页版.jpg",
        "/path/to/一个很笨但能成功写出SSCI的小tips_4_博士小导师_来自小红书网页版.jpg",
    ]
    
    sorted_files = parser.sort_files_by_page_number(test_files)
    print("排序后的文件:")
    for file_path in sorted_files:
        print(f"  {os.path.basename(file_path)}")
    
    # 测试文件系列验证
    is_valid, message = parser.validate_file_series(test_files)
    print(f"验证结果: {is_valid}, {message}")


if __name__ == "__main__":
    main()