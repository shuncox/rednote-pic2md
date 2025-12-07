"""
应用程序入口模块
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_window import main

if __name__ == "__main__":
    main()