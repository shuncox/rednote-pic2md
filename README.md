# 小红书图片转Markdown工具

一个基于Python和PyQt6的桌面应用程序，用于将小红书上的多页图片文章转换为Markdown格式的文档。

## 功能特点

- 🖼️ **智能文件识别**: 自动检测小红书系列图片文件
- 🔤 **多OCR服务支持**: 支持百度OCR、腾讯OCR、阿里云OCR
- 📝 **格式化输出**: 生成规范格式的Markdown文档
- 🎨 **友好界面**: 基于PyQt6的现代化用户界面
- ⚡ **高效处理**: 多线程处理，避免界面阻塞
- 💾 **自动保存**: 转换完成后自动保存，智能文件命名
- 🔧 **配置自动保存**: API配置自动保存，无需手动操作
- 🖼️ **智能图片处理**: 自动压缩超大图片，优化OCR识别





## 系统要求

- Python 3.8+
- 操作系统: Windows 10+、macOS 10.14+、Linux
- 网络连接（用于OCR服务）

## 快速开始

### 1. 环境准备

确保您的系统已安装Python 3.8或更高版本和uv包管理器。

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/shuncox/rednote-pic2md.git
cd rednote-pic2md

# 安装依赖
uv sync
```

### 3. 启动应用

```bash
uv run run.py
```

## 使用方法

1. **选择图片文件**: 点击"选择图片文件"按钮，选择一张小红书图片
2. **配置OCR服务**: 在设置面板中配置您的OCR服务API密钥（自动保存）
3. **设置输出选项**: 选择输出目录（可选，默认使用源文件目录）
4. **开始转换**: 点击"开始转换"按钮
5. **自动保存**: 转换完成后自动保存并显示保存路径

## OCR服务配置

### 百度OCR
- 需要API Key和Secret Key
- 申请地址: [百度智能云](https://console.bce.baidu.com/)

### 腾讯OCR
- 需要Secret Id和Secret Key
- 申请地址: [腾讯云](https://console.cloud.tencent.com/)

### 阿里云OCR
- 需要Access Key ID和Access Key Secret
- 申请地址: [阿里云](https://ecs.console.aliyun.com/)

## 支持的文件格式

- PNG
- JPG/JPEG
- BMP
- GIF
- WEBP

## 文件名格式

支持小红书标准文件名格式：
```
{标题}_{页码}_{作者}_来自小红书网页版.{扩展名}
```

示例：
```
一个小tip_2_导师_来自小红书网页版.jpg
```

## 项目结构

```
pic2md/
├── src/                    # 源代码目录
│   ├── __init__.py        # 包初始化文件
│   ├── app.py             # 应用程序入口
│   ├── main_window.py     # 主界面UI模块
│   ├── file_parser.py     # 文件名解析和排序模块
│   ├── ocr_service.py     # OCR服务集成模块
│   └── markdown_processor.py # Markdown处理模块
├── docs/                   # 文档目录
│   ├── design.md          # 设计文档
│   └── user_manual.md     # 用户手册
├── run.py                  # 启动脚本
├── test_core.py           # 核心功能测试
└── README.md              # 项目说明
```

## 开发说明

### 核心模块

- **main_window.py**: 主界面和用户交互
- **file_parser.py**: 文件名解析和系列文件检测
- **ocr_service.py**: OCR服务集成和管理
- **markdown_processor.py**: 文本处理和Markdown生成
- **config_manager.py**: 配置管理和自动保存
- **logger.py**: 日志系统和调试输出

### 测试

运行核心功能测试：
```bash
uv run test_core.py
```

## 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目遵循 MIT 许可证。详情请查看 [LICENSE](LICENSE) 文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件
- 参与讨论

## 更新日志

### v1.2.0 (2024-12-07)
- ✨ 移除保存按钮，实现转换后自动保存
- ✨ 智能文件命名，基于原文件名下划线前部分
- ✨ 统一分页处理，所有页面显示分页标记
- ✨ 调整日志等级至INFO，简化控制台输出
- 🔧 优化用户体验，减少操作步骤
- 🔧 改进文件名冲突处理机制

### v1.1.0 (2024-12-07)
- ✨ 新增配置自动保存功能
- ✨ 智能图片尺寸处理，自动压缩超大图片
- ✨ 完善的错误处理和用户提示
- ✨ 详细的日志系统
- 🐛 修复百度OCR图片格式错误问题
- 🐛 修复QPS超限控制问题
- 🔧 优化Markdown格式化输出
- 🔧 改进用户界面交互体验

### v1.0.0 (2024-12-07)
- 初始版本发布
- 支持多种OCR服务
- 实现文件系列自动检测
- 完成Markdown文档生成功能

---

**注意**: 使用本工具需要申请相应OCR服务的API密钥，请确保遵守各服务的使用条款和限制。
