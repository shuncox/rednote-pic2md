"""
主窗口UI模块
负责创建和管理应用程序的主界面
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QFileDialog,
    QMessageBox, QProgressBar, QTextEdit, QSplitter, QGroupBox,
    QLineEdit, QComboBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon

from file_parser import FileParser
from ocr_service import OcrService
from markdown_processor import MarkdownProcessor
from config_manager import get_config_manager
from logger import get_logger

logger = get_logger()


class FileListWidget(QListWidget):
    """自定义文件列表控件，支持拖拽排序"""
    
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        
    def dropEvent(self, event):
        """处理拖拽放置事件"""
        super().dropEvent(event)


class OcrWorker(QThread):
    """OCR处理工作线程"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_paths: List[str], ocr_config: dict, config_manager):
        super().__init__()
        logger.info(f"初始化OCR工作线程，文件数量: {len(file_paths)}")
        self.file_paths = file_paths
        self.ocr_config = ocr_config
        self.config_manager = config_manager
        self.file_parser = FileParser()
        self.ocr_service = OcrService()
        self.markdown_processor = MarkdownProcessor()
        
    def run(self):
        """执行OCR处理"""
        logger.info("开始执行OCR处理")
        try:
            # 设置OCR服务
            provider_name = self.ocr_config.get("service", "百度OCR")
            logger.info(f"使用OCR服务: {provider_name}")
            
            # 转换配置格式
            if provider_name == "百度OCR":
                config = {
                    "api_key": self.ocr_config.get("api_key", ""),
                    "secret_key": self.ocr_config.get("secret_key", "")
                }
            elif provider_name == "腾讯OCR":
                config = {
                    "secret_id": self.ocr_config.get("api_key", ""),
                    "secret_key": self.ocr_config.get("secret_key", ""),
                    "region": self.ocr_config.get("region", "ap-beijing")
                }
            elif provider_name == "阿里云OCR":
                config = {
                    "access_key_id": self.ocr_config.get("api_key", ""),
                    "access_key_secret": self.ocr_config.get("secret_key", ""),
                    "region": self.ocr_config.get("region", "cn-shanghai")
                }
            else:
                raise Exception(f"不支持的OCR服务: {provider_name}")
                
            # 获取QPS限制
            qps_limit = self.config_manager.get_qps_limit(provider_name)
            logger.info(f"QPS限制: {qps_limit}")
            
            # 初始化OCR服务
            logger.debug("初始化OCR服务")
            if not self.ocr_service.setup_provider(provider_name, config, qps_limit):
                raise Exception(f"设置OCR服务失败: {provider_name}")
                
            # 获取文件系列信息
            logger.debug("解析文件系列信息")
            series_info = self.file_parser.get_file_series_info(self.file_paths)
            title = series_info.get("title", "")
            author = series_info.get("author", "")
            logger.info(f"文档标题: {title}, 作者: {author}")
            
            # 处理每个文件
            pages = []
            for i, file_path in enumerate(self.file_paths):
                file_name = os.path.basename(file_path)
                logger.info(f"处理文件 {i+1}/{len(self.file_paths)}: {file_name}")
                
                self.progress_updated.emit(int((i + 1) / len(self.file_paths) * 50))  # 前50%用于OCR
                self.status_updated.emit(f"正在处理第{i+1}/{len(self.file_paths)}页: {file_name}")
                
                try:
                    # 验证文件存在
                    if not os.path.exists(file_path):
                        raise Exception(f"文件不存在: {file_name}")
                    
                    # OCR识别
                    logger.debug(f"开始OCR识别: {file_name}")
                    self.status_updated.emit(f"正在识别文字: {file_name}")
                    ocr_text = self.ocr_service.recognize_image(file_path)
                    logger.debug(f"OCR识别完成，文字长度: {len(ocr_text)}")
                    
                    # 检查识别结果
                    if not ocr_text or ocr_text.strip() == "":
                        logger.warning(f"文件 {file_name} 未识别到文字内容")
                        self.status_updated.emit(f"警告: {file_name} 未识别到文字内容")
                        ocr_text = f"[第{i+1}页 - 未识别到文字内容]"
                    
                    # 处理页面内容
                    logger.debug(f"处理页面内容: {file_name}")
                    self.status_updated.emit(f"正在处理内容: {file_name}")
                    page_content = self.markdown_processor.process_page_content(i + 1, ocr_text)
                    pages.append(page_content)
                    
                except Exception as e:
                    error_msg = f"处理文件 {file_name} 失败: {str(e)}"
                    logger.error(error_msg)
                    self.status_updated.emit(f"错误: {error_msg}")
                    raise Exception(error_msg)
                    
            # 生成Markdown文档
            logger.info("生成Markdown文档")
            self.progress_updated.emit(75)
            self.status_updated.emit("正在生成Markdown文档...")
            
            markdown_content = self.markdown_processor.generate_markdown(pages, title, author)
            logger.debug(f"Markdown文档长度: {len(markdown_content)}")
            
            # 格式化Markdown
            logger.debug("格式化Markdown文档")
            self.progress_updated.emit(90)
            self.status_updated.emit("正在格式化文档...")
            
            formatted_markdown = self.markdown_processor.format_markdown_structure(markdown_content)
            
            self.progress_updated.emit(100)
            self.status_updated.emit("转换完成")
            logger.info("OCR处理完成")
            
            self.finished.emit(formatted_markdown)
            
        except Exception as e:
            logger.error(f"OCR处理失败: {str(e)}")
            self.error_occurred.emit(f"处理过程中发生错误: {str(e)}")


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        logger.info("初始化主窗口")
        self.selected_files: List[str] = []
        self.ocr_worker: Optional[OcrWorker] = None
        self.config_manager = get_config_manager()
        
        self.init_ui()
        self.setup_connections()
        self.load_settings()
        logger.info("主窗口初始化完成")
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("小红书图片转Markdown")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧面板
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([400, 800])
        
    def create_left_panel(self) -> QWidget:
        """创建左侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 文件选择组
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout(file_group)
        
        # 选择文件按钮
        self.select_file_btn = QPushButton("选择图片文件")
        self.select_file_btn.setMinimumHeight(40)
        file_layout.addWidget(self.select_file_btn)
        
        # 文件列表
        self.file_list = FileListWidget()
        self.file_list.setMinimumHeight(200)
        file_layout.addWidget(self.file_list)
        
        # 文件操作按钮
        file_ops_layout = QHBoxLayout()
        self.add_file_btn = QPushButton("添加")
        self.remove_file_btn = QPushButton("删除")
        self.clear_file_btn = QPushButton("清空")
        file_ops_layout.addWidget(self.add_file_btn)
        file_ops_layout.addWidget(self.remove_file_btn)
        file_ops_layout.addWidget(self.clear_file_btn)
        file_layout.addLayout(file_ops_layout)
        
        layout.addWidget(file_group)
        
        # OCR设置组
        ocr_group = QGroupBox("OCR设置")
        ocr_layout = QVBoxLayout(ocr_group)
        
        # OCR服务选择
        ocr_service_layout = QHBoxLayout()
        ocr_service_layout.addWidget(QLabel("OCR服务:"))
        self.ocr_service_combo = QComboBox()
        self.ocr_service_combo.addItems(["百度OCR", "腾讯OCR", "阿里云OCR"])
        ocr_service_layout.addWidget(self.ocr_service_combo)
        ocr_layout.addLayout(ocr_service_layout)
        
        # API Key输入
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("请输入API Key")
        api_key_layout.addWidget(self.api_key_input)
        ocr_layout.addLayout(api_key_layout)
        
        # Secret Key输入（百度OCR需要）
        secret_key_layout = QHBoxLayout()
        secret_key_layout.addWidget(QLabel("Secret Key:"))
        self.secret_key_input = QLineEdit()
        self.secret_key_input.setPlaceholderText("百度OCR需要Secret Key")
        secret_key_layout.addWidget(self.secret_key_input)
        ocr_layout.addLayout(secret_key_layout)
        
        layout.addWidget(ocr_group)
        
        # 输出设置组
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout(output_group)
        
        # 输出目录选择
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(QLabel("输出目录:"))
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("默认为源文件所在目录")
        self.output_dir_btn = QPushButton("选择")
        output_dir_layout.addWidget(self.output_dir_input)
        output_dir_layout.addWidget(self.output_dir_btn)
        output_layout.addLayout(output_dir_layout)
        
        # 输出文件名
        output_name_layout = QHBoxLayout()
        output_name_layout.addWidget(QLabel("文件名:"))
        self.output_name_input = QLineEdit()
        self.output_name_input.setPlaceholderText("输出文件名（不含扩展名）")
        output_name_layout.addWidget(self.output_name_input)
        output_layout.addLayout(output_name_layout)
        
        
        
        layout.addWidget(output_group)
        
        # 转换控制
        control_group = QGroupBox("转换控制")
        control_layout = QVBoxLayout(control_group)
        
        # 转换按钮
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setMinimumHeight(50)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_layout.addWidget(self.convert_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        control_layout.addWidget(self.status_label)
        
        layout.addWidget(control_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        return panel
        
    def create_right_panel(self) -> QWidget:
        """创建右侧预览面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 预览组
        preview_group = QGroupBox("Markdown预览")
        preview_layout = QVBoxLayout(preview_group)
        
        # 预览文本区域
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Monaco", 12))
        preview_layout.addWidget(self.preview_text)
        
        
        
        layout.addWidget(preview_group)
        
        return panel
        
    def setup_connections(self):
        """设置信号连接"""
        # 文件选择相关
        self.select_file_btn.clicked.connect(self.select_file)
        self.add_file_btn.clicked.connect(self.add_file)
        self.remove_file_btn.clicked.connect(self.remove_file)
        self.clear_file_btn.clicked.connect(self.clear_files)
        
        # 输出目录选择
        self.output_dir_btn.clicked.connect(self.select_output_directory)
        
        # 转换控制
        self.convert_btn.clicked.connect(self.start_conversion)
        
        # OCR服务选择变化
        self.ocr_service_combo.currentTextChanged.connect(self.on_ocr_service_changed)
        
        # API配置变化时自动保存（使用延迟保存避免频繁写入）
        self.api_key_input.textChanged.connect(self.delayed_auto_save)
        self.secret_key_input.textChanged.connect(self.delayed_auto_save)
        self.ocr_service_combo.currentTextChanged.connect(self.auto_save_ocr_settings)
        self.output_dir_input.textChanged.connect(self.delayed_auto_save)
        
    def select_file(self):
        """选择图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*)"
        )
        
        if file_path:
            self.add_file_to_list(file_path)
            self.auto_detect_series_files(file_path)
            
    def add_file(self):
        """添加文件到列表"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*)"
        )
        
        for file_path in file_paths:
            self.add_file_to_list(file_path)
            
    def add_file_to_list(self, file_path: str):
        """添加单个文件到列表"""
        if file_path not in self.selected_files:
            self.selected_files.append(file_path)
            item = QListWidgetItem(os.path.basename(file_path))
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.file_list.addItem(item)
            
    def remove_file(self):
        """删除选中的文件"""
        current_row = self.file_list.currentRow()
        if current_row >= 0:
            item = self.file_list.takeItem(current_row)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
                
    def clear_files(self):
        """清空文件列表"""
        self.file_list.clear()
        self.selected_files.clear()
        
    def auto_detect_series_files(self, selected_file: str):
        """自动检测系列文件"""
        file_parser = FileParser()
        series_files = file_parser.detect_series_files(selected_file)
        
        # 清空当前列表
        self.clear_files()
        
        # 添加检测到的文件
        for file_path in series_files:
            self.add_file_to_list(file_path)
            
        # 更新状态
        if len(series_files) > 1:
            self.status_label.setText(f"自动检测到 {len(series_files)} 个系列文件")
        else:
            self.status_label.setText("未检测到系列文件")
        
    def select_output_directory(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_input.setText(dir_path)
            
    def on_ocr_service_changed(self, service_name: str):
        """OCR服务选择变化时的处理"""
        if service_name == "百度OCR":
            self.secret_key_input.setEnabled(True)
        else:
            self.secret_key_input.setEnabled(False)
            
    def start_conversion(self):
        """开始转换"""
        logger.info("开始转换流程")
        
        if not self.selected_files:
            logger.warning("没有选择文件")
            QMessageBox.warning(self, "警告", "请先选择要转换的图片文件")
            return
            
        logger.info(f"选择了 {len(self.selected_files)} 个文件")
        
        # 检查API配置
        api_key = self.api_key_input.text().strip()
        if not api_key:
            logger.warning("API Key为空")
            QMessageBox.warning(self, "警告", "请输入API Key")
            return
            
        # 自动保存当前设置
        logger.debug("保存当前设置")
        self.save_settings()
            
        # 禁用转换按钮
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("转换中...")
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建OCR工作线程
        ocr_config = {
            "service": self.ocr_service_combo.currentText(),
            "api_key": api_key,
            "secret_key": self.secret_key_input.text().strip() if self.secret_key_input.isEnabled() else ""
        }
        
        logger.info(f"使用OCR服务: {ocr_config['service']}")
        
        self.ocr_worker = OcrWorker(self.selected_files, ocr_config, self.config_manager)
        self.ocr_worker.progress_updated.connect(self.update_progress)
        self.ocr_worker.status_updated.connect(self.update_status)
        self.ocr_worker.finished.connect(self.on_conversion_finished)
        self.ocr_worker.error_occurred.connect(self.on_conversion_error)
        
        logger.info("启动OCR工作线程")
        self.ocr_worker.start()
        
    def update_progress(self, value: int):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
    def update_status(self, status: str):
        """更新状态标签"""
        self.status_label.setText(status)
        
    def on_conversion_finished(self, markdown_content: str):
        """转换完成处理"""
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("开始转换")
        self.progress_bar.setVisible(False)
        self.status_label.setText("转换完成")
        
        # 显示预览
        self.preview_text.setPlainText(markdown_content)
        
        # 自动保存文件
        try:
            output_path = self.generate_output_path(markdown_content)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            QMessageBox.information(self, "完成", f"图片转换完成！\n文件已保存到: {output_path}")
            logger.info(f"文件已自动保存: {output_path}")
            
        except Exception as e:
            logger.error(f"自动保存文件失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"转换完成但保存文件失败: {str(e)}")
        
    def on_conversion_error(self, error_message: str):
        """转换错误处理"""
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("开始转换")
        self.progress_bar.setVisible(False)
        self.status_label.setText("转换失败")
        
        # 分析错误类型并提供解决建议
        suggestion = self._get_error_suggestion(error_message)
        
        if suggestion:
            full_message = f"{error_message}\n\n解决建议:\n{suggestion}"
        else:
            full_message = error_message
            
        QMessageBox.critical(self, "转换错误", full_message)
        
    def _get_error_suggestion(self, error_message: str) -> str:
        """
        根据错误消息提供解决建议
        
        Args:
            error_message: 错误消息
            
        Returns:
            解决建议
        """
        error_message = error_message.lower()
        
        if "图片文件不存在" in error_message:
            return "请检查图片文件路径是否正确，确保文件存在且可访问。"
        elif "路径不是文件" in error_message:
            return "请选择正确的图片文件，而不是文件夹。"
        elif "不支持的图片格式" in error_message:
            return "请使用支持的图片格式：JPG、JPEG、PNG、BMP、GIF、WEBP。"
        elif "图片文件为空" in error_message:
            return "图片文件似乎损坏或为空，请重新获取图片文件。"
        elif "图片文件过大" in error_message:
            return "图片文件太大，请压缩图片或使用较小的图片文件（小于8MB）。"
        elif "读取图片文件失败" in error_message:
            return "无法读取图片文件，请检查文件权限或重新选择文件。"
        elif "认证失败" in error_message or "api key" in error_message:
            return "请检查API密钥配置是否正确，确保密钥有效且有足够的权限。"
        elif "qps超限" in error_message:
            return "请求频率过高，请稍后重试或考虑升级OCR服务套餐。"
        elif "网络" in error_message or "连接" in error_message:
            return "网络连接问题，请检查网络设置或稍后重试。"
        elif "超时" in error_message:
            return "请求超时，请检查网络连接或稍后重试。"
        elif "未能识别出文字" in error_message:
            return "图片中可能没有清晰的文字，请使用更清晰的图片。"
        else:
            return "请检查图片文件和OCR配置，或联系技术支持获取帮助。"
        
    def generate_output_path(self, markdown_content: str) -> str:
        """
        生成输出文件路径
        
        Args:
            markdown_content: Markdown内容
            
        Returns:
            完整的输出文件路径
        """
        # 确定输出目录
        output_dir = self.output_dir_input.text().strip()
        if not output_dir:
            # 默认使用第一个文件的目录
            output_dir = os.path.dirname(self.selected_files[0])
        
        # 生成基础文件名（使用第一个文件的下划线之前的部分）
        first_filename = os.path.basename(self.selected_files[0])
        base_name = self.extract_base_name(first_filename)
        
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 检查文件是否存在，如果存在则添加编号
        output_path = os.path.join(output_dir, f"{base_name}.md")
        counter = 1
        
        while os.path.exists(output_path):
            output_path = os.path.join(output_dir, f"{base_name}_{counter}.md")
            counter += 1
            
        return output_path
        
    def extract_base_name(self, filename: str) -> str:
        """
        从文件名中提取基础名称（下划线之前的部分）
        
        Args:
            filename: 原始文件名
            
        Returns:
            提取的基础名称
        """
        # 移除扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 按下划线分割，取第一部分
        parts = name_without_ext.split('_')
        if len(parts) >= 2:
            base_name = parts[0]
        else:
            base_name = name_without_ext
            
        # 清理文件名，移除不合法字符
        import re
        base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)
        base_name = base_name.strip(' _')
        
        # 确保不为空
        if not base_name:
            base_name = "converted_document"
            
        return base_name
            
    def load_settings(self):
        """加载保存的设置"""
        # 加载OCR设置
        ocr_config = self.config_manager.load_config()["ocr"]
        self.ocr_service_combo.setCurrentText(ocr_config["service"])
        
        # 加载对应服务的配置
        service_name = ocr_config["service"]
        service_config = self.config_manager.get_ocr_config(service_name)
        
        if service_name == "百度OCR":
            self.api_key_input.setText(service_config.get("api_key", ""))
            self.secret_key_input.setText(service_config.get("secret_key", ""))
        elif service_name == "腾讯OCR":
            self.api_key_input.setText(service_config.get("secret_id", ""))
            self.secret_key_input.setText(service_config.get("secret_key", ""))
        elif service_name == "阿里云OCR":
            self.api_key_input.setText(service_config.get("access_key_id", ""))
            self.secret_key_input.setText(service_config.get("access_key_secret", ""))
            
        # 加载输出设置
        output_config = self.config_manager.get_output_config()
        self.output_dir_input.setText(output_config.get("directory", ""))
        
    def save_settings(self):
        """保存当前设置（自动保存）"""
        # 保存OCR设置
        service_name = self.ocr_service_combo.currentText()
        ocr_config = {"service": service_name}
        
        if service_name == "百度OCR":
            service_config = {
                "api_key": self.api_key_input.text().strip(),
                "secret_key": self.secret_key_input.text().strip()
            }
        elif service_name == "腾讯OCR":
            service_config = {
                "secret_id": self.api_key_input.text().strip(),
                "secret_key": self.secret_key_input.text().strip()
            }
        elif service_name == "阿里云OCR":
            service_config = {
                "access_key_id": self.api_key_input.text().strip(),
                "access_key_secret": self.secret_key_input.text().strip()
            }
        else:
            service_config = {}
            
        self.config_manager.update_ocr_config(service_name, service_config)
        
        # 保存输出设置
        output_config = {
            "directory": self.output_dir_input.text().strip()
        }
        self.config_manager.update_output_config(output_config)
        
    def auto_save_ocr_settings(self):
        """自动保存OCR设置"""
        logger.debug("自动保存OCR设置")
        self.save_settings()
        
    def delayed_auto_save(self):
        """延迟自动保存设置"""
        # 使用QTimer延迟保存，避免频繁写入
        if not hasattr(self, '_auto_save_timer'):
            from PyQt6.QtCore import QTimer
            self._auto_save_timer = QTimer()
            self._auto_save_timer.setSingleShot(True)
            self._auto_save_timer.timeout.connect(self.auto_save_ocr_settings)
        
        # 重启定时器（1秒后保存）
        self._auto_save_timer.stop()
        self._auto_save_timer.start(1000)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("小红书图片转Markdown")
    app.setOrganizationName("Pic2MD")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
