"""
配置管理模块
负责保存和加载应用程序设置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为用户主目录下的.pic2md
        """
        if config_dir is None:
            home_dir = Path.home()
            self.config_dir = home_dir / ".pic2md"
        else:
            self.config_dir = Path(config_dir)
            
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.config_file = self.config_dir / "config.json"
        
        # 默认配置
        self.default_config = {
            "ocr": {
                "service": "百度OCR",
                "baidu": {
                    "api_key": "",
                    "secret_key": ""
                },
                "tencent": {
                    "secret_id": "",
                    "secret_key": "",
                    "region": "ap-beijing"
                },
                "aliyun": {
                    "access_key_id": "",
                    "access_key_secret": "",
                    "region": "cn-shanghai"
                }
            },
            "output": {
                "directory": "",
                "filename_pattern": "{title}"
            },
            "ui": {
                "window_geometry": "",
                "splitter_state": ""
            },
            "performance": {
                "baidu_qps": 2,
                "tencent_qps": 5,
                "aliyun_qps": 5
            }
        }
        
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置
        
        Returns:
            配置字典
        """
        if not self.config_file.exists():
            return self.default_config.copy()
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 合并默认配置，确保所有必要的键都存在
            merged_config = self.default_config.copy()
            self._deep_update(merged_config, config)
            
            return merged_config
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载配置文件失败: {e}")
            return self.default_config.copy()
            
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置
        
        Args:
            config: 要保存的配置字典
            
        Returns:
            保存是否成功
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
            
        except IOError as e:
            print(f"保存配置文件失败: {e}")
            return False
            
    def get_ocr_config(self, service_name: str) -> Dict[str, str]:
        """
        获取特定OCR服务的配置
        
        Args:
            service_name: OCR服务名称
            
        Returns:
            OCR服务配置
        """
        config = self.load_config()
        service_key = service_name.lower().replace("ocr", "")
        
        if service_key == "百度":
            return config["ocr"]["baidu"]
        elif service_key == "腾讯":
            return config["ocr"]["tencent"]
        elif service_key == "阿里云":
            return config["ocr"]["aliyun"]
        else:
            return {}
            
    def update_ocr_config(self, service_name: str, service_config: Dict[str, str]) -> bool:
        """
        更新特定OCR服务的配置
        
        Args:
            service_name: OCR服务名称
            service_config: 服务配置
            
        Returns:
            更新是否成功
        """
        config = self.load_config()
        service_key = service_name.lower().replace("ocr", "")
        
        if service_key == "百度":
            config["ocr"]["baidu"].update(service_config)
        elif service_key == "腾讯":
            config["ocr"]["tencent"].update(service_config)
        elif service_key == "阿里云":
            config["ocr"]["aliyun"].update(service_config)
        else:
            return False
            
        return self.save_config(config)
        
    def get_output_config(self) -> Dict[str, str]:
        """
        获取输出配置
        
        Returns:
            输出配置
        """
        config = self.load_config()
        return config["output"]
        
    def update_output_config(self, output_config: Dict[str, str]) -> bool:
        """
        更新输出配置
        
        Args:
            output_config: 输出配置
            
        Returns:
            更新是否成功
        """
        config = self.load_config()
        config["output"].update(output_config)
        return self.save_config(config)
        
    def get_ui_config(self) -> Dict[str, str]:
        """
        获取UI配置
        
        Returns:
            UI配置
        """
        config = self.load_config()
        return config["ui"]
        
    def update_ui_config(self, ui_config: Dict[str, str]) -> bool:
        """
        更新UI配置
        
        Args:
            ui_config: UI配置
            
        Returns:
            更新是否成功
        """
        config = self.load_config()
        config["ui"].update(ui_config)
        return self.save_config(config)
        
    def get_qps_limit(self, service_name: str) -> int:
        """
        获取服务的QPS限制
        
        Args:
            service_name: OCR服务名称
            
        Returns:
            QPS限制值
        """
        config = self.load_config()
        service_key = service_name.lower().replace("ocr", "")
        
        if service_key == "百度":
            return config["performance"]["baidu_qps"]
        elif service_key == "腾讯":
            return config["performance"]["tencent_qps"]
        elif service_key == "阿里云":
            return config["performance"]["aliyun_qps"]
        else:
            return 2  # 默认限制
            
    def update_qps_limit(self, service_name: str, qps_limit: int) -> bool:
        """
        更新服务的QPS限制
        
        Args:
            service_name: OCR服务名称
            qps_limit: QPS限制值
            
        Returns:
            更新是否成功
        """
        config = self.load_config()
        service_key = service_name.lower().replace("ocr", "")
        
        if service_key == "百度":
            config["performance"]["baidu_qps"] = qps_limit
        elif service_key == "腾讯":
            config["performance"]["tencent_qps"] = qps_limit
        elif service_key == "阿里云":
            config["performance"]["aliyun_qps"] = qps_limit
        else:
            return False
            
        return self.save_config(config)
        
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """
        深度更新字典
        
        Args:
            base_dict: 基础字典
            update_dict: 更新字典
        """
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def main():
    """测试函数"""
    config_manager = ConfigManager()
    
    # 测试加载配置
    config = config_manager.load_config()
    print("默认配置:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    # 测试更新OCR配置
    baidu_config = {
        "api_key": "test_api_key",
        "secret_key": "test_secret_key"
    }
    
    success = config_manager.update_ocr_config("百度OCR", baidu_config)
    print(f"\n更新百度OCR配置: {success}")
    
    # 测试获取OCR配置
    baidu_config = config_manager.get_ocr_config("百度OCR")
    print(f"百度OCR配置: {baidu_config}")
    
    # 测试QPS限制
    qps = config_manager.get_qps_limit("百度OCR")
    print(f"百度OCR QPS限制: {qps}")


if __name__ == "__main__":
    main()
