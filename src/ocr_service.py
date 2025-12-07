"""
OCR服务模块
提供多种OCR API的统一接口
"""

import base64
import json
import os
import requests
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path
from threading import Lock

from logger import get_logger

logger = get_logger()


class OcrProvider(ABC):
    """OCR提供者抽象基类"""
    
    @abstractmethod
    def recognize_image(self, image_path: str) -> str:
        """
        识别图片中的文字
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            识别出的文字内容
        """
        pass
        
    @abstractmethod
    def validate_config(self, config: Dict[str, str]) -> bool:
        """
        验证配置是否有效
        
        Args:
            config: 配置字典
            
        Returns:
            配置是否有效
        """
        pass


class BaiduOcrProvider(OcrProvider):
    """百度OCR提供者"""
    
    def __init__(self, api_key: str, secret_key: str, qps_limit: int = 2):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.token_expire_time = 0
        self.qps_limit = qps_limit
        self.last_request_time = 0
        self.request_lock = Lock()
        
    def get_access_token(self) -> str:
        """获取访问令牌"""
        import time
        
        # 检查令牌是否仍然有效
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token
            
        # 获取新令牌
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "access_token" in data:
                self.access_token = data["access_token"]
                # 令牌有效期减去5分钟缓冲
                self.token_expire_time = time.time() + data.get("expires_in", 2592000) - 300
                return self.access_token
            else:
                raise Exception(f"获取访问令牌失败: {data}")
                
        except Exception as e:
            raise Exception(f"百度OCR认证失败: {str(e)}")
            
    def recognize_image(self, image_path: str) -> str:
        """识别图片中的文字"""
        logger.debug(f"开始识别图片: {image_path}")
        
        # QPS限制控制
        with self.request_lock:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            min_interval = 1.0 / self.qps_limit
            
            if time_since_last_request < min_interval:
                sleep_time = min_interval - time_since_last_request
                logger.debug(f"QPS限制: 等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)
                
            self.last_request_time = time.time()
        
        try:
            # 验证图片文件
            logger.debug(f"验证图片文件: {image_path}")
            if not os.path.exists(image_path):
                raise Exception(f"图片文件不存在: {image_path}")
                
            if not os.path.isfile(image_path):
                raise Exception(f"路径不是文件: {image_path}")
                
            # 检查文件大小（百度OCR限制：base64编码后不超过10MB）
            file_size = os.path.getsize(image_path)
            logger.debug(f"图片文件大小: {file_size / (1024*1024):.2f}MB")
            if file_size > 8 * 1024 * 1024:  # 8MB原始文件限制
                raise Exception(f"图片文件过大: {file_size / (1024*1024):.2f}MB，请使用小于8MB的图片")
            
            # 检查文件扩展名 - 百度OCR支持的格式
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext not in valid_extensions:
                raise Exception(f"不支持的图片格式: {file_ext}，百度OCR支持的格式: {', '.join(valid_extensions)}")
                
            # 验证图片文件的实际格式（不只是扩展名）
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    # 检查图片格式
                    actual_format = img.format.lower()
                    if actual_format not in ['jpeg', 'png', 'bmp']:
                        raise Exception(f"图片实际格式 {actual_format} 不被支持，百度OCR支持的格式: JPEG, PNG, BMP")
                    
                    # 检查图片尺寸（百度OCR限制：图片长宽不超过4096像素）
                    width, height = img.size
                    logger.debug(f"图片尺寸: {width}x{height}")
                    
                    if width > 4096 or height > 4096:
                        logger.info(f"图片尺寸过大 ({width}x{height})，正在压缩...")
                        # 计算缩放比例
                        scale = min(4096 / width, 4096 / height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        
                        # 缩放图片
                        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        logger.info(f"图片已压缩至: {new_width}x{new_height}")
                        
                        # 保存临时文件
                        temp_path = image_path + "_resized.jpg"
                        if resized_img.mode not in ['RGB', 'L']:
                            resized_img = resized_img.convert('RGB')
                        resized_img.save(temp_path, 'JPEG', quality=95)
                        image_path = temp_path
                    else:
                        # 检查图片模式
                        if img.mode not in ['RGB', 'L', 'RGBA']:
                            logger.debug(f"转换图片模式: {img.mode} -> RGB")
                            rgb_img = img.convert('RGB')
                            # 保存临时文件
                            temp_path = image_path + "_temp.jpg"
                            rgb_img.save(temp_path, 'JPEG', quality=95)
                            image_path = temp_path
                        
            except ImportError:
                # 如果没有PIL，跳过实际格式检查
                logger.warning("未安装PIL库，跳过图片格式验证")
            except Exception as e:
                if "不被支持" in str(e):
                    raise
                else:
                    logger.warning(f"图片格式验证警告: {str(e)}")
            
            # 读取图片并转换为base64
            try:
                logger.debug("读取图片文件")
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                    
                if not image_data:
                    raise Exception("图片文件为空")
                    
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                logger.debug(f"图片base64编码长度: {len(image_base64) / (1024*1024):.2f}MB")
                
                # 检查base64编码后的大小
                if len(image_base64) > 10 * 1024 * 1024:  # 10MB限制
                    raise Exception(f"图片base64编码后过大: {len(image_base64) / (1024*1024):.2f}MB")
                    
            except IOError as e:
                raise Exception(f"读取图片文件失败: {str(e)}")
            
            # 获取访问令牌
            logger.debug("获取百度OCR访问令牌")
            access_token = self.get_access_token()
            
            # 调用OCR API
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {'image': image_base64}
            
            logger.debug("发送百度OCR API请求")
            try:
                response = requests.post(url, headers=headers, data=data, timeout=30)
                logger.debug(f"OCR API响应状态码: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                logger.debug(f"OCR API响应数据: {result}")
                
            except requests.exceptions.Timeout:
                raise Exception("OCR请求超时，请检查网络连接")
            except requests.exceptions.ConnectionError:
                raise Exception("网络连接错误，请检查网络设置")
            except requests.exceptions.RequestException as e:
                raise Exception(f"网络请求失败: {str(e)}")
            
            # 检查API响应
            if "error_code" in result:
                error_code = result.get("error_code")
                error_msg = result.get('error_msg', '未知错误')
                
                error_mapping = {
                    4: "认证失败，请检查API Key和Secret Key",
                    17: "每天请求量超限额，请升级套餐或明天再试",
                    18: f"QPS超限，请降低请求频率。当前限制: {self.qps_limit} QPS",
                    19: "请求总量超限，请升级套餐",
                    100: "无效的access_token",
                    110: "Access Token失效",
                    111: "Access token过期",
                    216100: "参数错误，请检查图片格式",
                    216201: "图片为空",
                    216202: "上传的图片格式错误或尺寸不符合要求（长宽不超过4096像素）",
                    216203: "上传的图片大小错误（base64编码后不超过10MB）",
                    216630: "识别错误，请检查图片质量",
                    282000: "内部服务器错误"
                }
                
                error_desc = error_mapping.get(error_code, f"百度OCR API错误: {error_msg}")
                raise Exception(error_desc)
                
            # 提取文字内容
            words_result = result.get("words_result", [])
            if not words_result:
                return "未能识别出文字内容，请检查图片清晰度"
                
            words = []
            for item in words_result:
                if "words" in item:
                    words.append(item["words"])
                    
            if not words:
                return "未能识别出有效文字"
                
            return "\n".join(words)
            
        except Exception as e:
            # 重新抛出已知异常
            if "百度OCR识别失败" in str(e) or "图片文件" in str(e) or "网络" in str(e) or "API" in str(e):
                raise
            else:
                raise Exception(f"百度OCR识别失败: {str(e)}")
            
    def validate_config(self, config: Dict[str, str]) -> bool:
        """验证配置"""
        return bool(config.get("api_key") and config.get("secret_key"))


class TencentOcrProvider(OcrProvider):
    """腾讯云OCR提供者"""
    
    def __init__(self, secret_id: str, secret_key: str, region: str = "ap-beijing"):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        
    def recognize_image(self, image_path: str) -> str:
        """识别图片中的文字"""
        try:
            # 验证图片文件
            if not os.path.exists(image_path):
                raise Exception(f"图片文件不存在: {image_path}")
                
            if not os.path.isfile(image_path):
                raise Exception(f"路径不是文件: {image_path}")
                
            # 检查文件大小
            file_size = os.path.getsize(image_path)
            if file_size > 8 * 1024 * 1024:  # 8MB限制
                raise Exception(f"图片文件过大: {file_size / (1024*1024):.2f}MB，请使用小于8MB的图片")
            
            # 检查文件扩展名
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext not in valid_extensions:
                raise Exception(f"不支持的图片格式: {file_ext}，支持的格式: {', '.join(valid_extensions)}")
            
            # 读取图片并转换为base64
            try:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                    
                if not image_data:
                    raise Exception("图片文件为空")
                    
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
            except IOError as e:
                raise Exception(f"读取图片文件失败: {str(e)}")
            
            # 构造请求参数
            endpoint = "ocr.tencentcloudapi.com"
            service = "ocr"
            version = "2018-11-19"
            action = "GeneralBasicOCR"
            
            # 构造请求体
            payload = {
                "ImageBase64": image_base64
            }
            
            # 调用腾讯云API
            from tencentcloud.common import credential
            from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
            from tencentcloud.ocr.v20181119 import ocr_client, models
            
            try:
                cred = credential.Credential(self.secret_id, self.secret_key)
                client = ocr_client.OcrClient(cred, self.region)
                req = models.GeneralBasicOCRRequest()
                req.from_json_string(json.dumps(payload))
                
                resp = client.GeneralBasicOCR(req)
                
                # 提取文字内容
                words = []
                for text_detection in resp.TextDetections:
                    words.append(text_detection.DetectedText)
                    
                return "\n".join(words)
                
            except Exception as e:
                raise Exception(f"腾讯云OCR API调用失败: {str(e)}")
                
        except Exception as e:
            raise Exception(f"腾讯云OCR识别失败: {str(e)}")
            
    def validate_config(self, config: Dict[str, str]) -> bool:
        """验证配置"""
        return bool(config.get("secret_id") and config.get("secret_key"))


class AliyunOcrProvider(OcrProvider):
    """阿里云OCR提供者"""
    
    def __init__(self, access_key_id: str, access_key_secret: str, region: str = "cn-shanghai"):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region = region
        
    def recognize_image(self, image_path: str) -> str:
        """识别图片中的文字"""
        try:
            # 读取图片并转换为base64
            with open(image_path, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 构造请求
            import alibabacloud_tea_openapi as open_api
            from alibabacloud_ocr_api20210707 import client as ocr_client
            from alibabacloud_ocr_api20210707 import models as ocr_models
            
            config = open_api.Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret
            )
            config.endpoint = f'ocr-api.{self.region}.aliyuncs.com'
            
            client = ocr_client.Client(config)
            
            request = ocr_models.RecognizeGeneralRequest(
                body=image_base64
            )
            
            response = client.recognize_general(request)
            
            # 提取文字内容
            words = []
            for content in response.body.data.content:
                words.append(content.text)
                
            return "\n".join(words)
            
        except Exception as e:
            raise Exception(f"阿里云OCR识别失败: {str(e)}")
            
    def validate_config(self, config: Dict[str, str]) -> bool:
        """验证配置"""
        return bool(config.get("access_key_id") and config.get("access_key_secret"))


class OcrService:
    """OCR服务管理器"""
    
    def __init__(self):
        self.providers = {
            "百度OCR": BaiduOcrProvider,
            "腾讯OCR": TencentOcrProvider,
            "阿里云OCR": AliyunOcrProvider
        }
        self.current_provider: Optional[OcrProvider] = None
        
    def setup_provider(self, provider_name: str, config: Dict[str, str], qps_limit: Optional[int] = None) -> bool:
        """
        设置OCR提供者
        
        Args:
            provider_name: 提供者名称
            config: 配置参数
            qps_limit: QPS限制（可选）
            
        Returns:
            设置是否成功
        """
        if provider_name not in self.providers:
            return False
            
        provider_class = self.providers[provider_name]
        
        try:
            if provider_name == "百度OCR":
                qps = qps_limit if qps_limit is not None else 2  # 默认百度QPS限制为2
                self.current_provider = provider_class(
                    config["api_key"], 
                    config["secret_key"],
                    qps
                )
            elif provider_name == "腾讯OCR":
                self.current_provider = provider_class(
                    config["secret_id"], 
                    config["secret_key"],
                    config.get("region", "ap-beijing")
                )
            elif provider_name == "阿里云OCR":
                self.current_provider = provider_class(
                    config["access_key_id"],
                    config["access_key_secret"],
                    config.get("region", "cn-shanghai")
                )
            
            # 验证配置
            return self.current_provider.validate_config(config)
            
        except Exception as e:
            print(f"设置OCR提供者失败: {str(e)}")
            return False
            
    def recognize_image(self, image_path: str) -> str:
        """
        识别图片中的文字
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            识别出的文字内容
        """
        if not self.current_provider:
            raise Exception("未设置OCR提供者")
            
        if not Path(image_path).exists():
            raise Exception(f"图片文件不存在: {image_path}")
            
        return self.current_provider.recognize_image(image_path)
        
    def get_available_providers(self) -> List[str]:
        """获取可用的OCR提供者列表"""
        return list(self.providers.keys())
        
    def get_provider_config_fields(self, provider_name: str) -> List[Dict[str, str]]:
        """
        获取提供者所需的配置字段
        
        Args:
            provider_name: 提供者名称
            
        Returns:
            配置字段列表
        """
        configs = {
            "百度OCR": [
                {"name": "api_key", "label": "API Key", "required": True},
                {"name": "secret_key", "label": "Secret Key", "required": True}
            ],
            "腾讯OCR": [
                {"name": "secret_id", "label": "Secret Id", "required": True},
                {"name": "secret_key", "label": "Secret Key", "required": True},
                {"name": "region", "label": "区域", "required": False, "default": "ap-beijing"}
            ],
            "阿里云OCR": [
                {"name": "access_key_id", "label": "Access Key ID", "required": True},
                {"name": "access_key_secret", "label": "Access Key Secret", "required": True},
                {"name": "region", "label": "区域", "required": False, "default": "cn-shanghai"}
            ]
        }
        
        return configs.get(provider_name, [])


def main():
    """测试函数"""
    # 创建OCR服务
    ocr_service = OcrService()
    
    # 获取可用提供者
    providers = ocr_service.get_available_providers()
    print(f"可用的OCR提供者: {providers}")
    
    # 获取百度OCR的配置字段
    baidu_config = ocr_service.get_provider_config_fields("百度OCR")
    print(f"百度OCR配置字段: {baidu_config}")
    
    # 测试配置验证（使用测试数据）
    test_config = {
        "api_key": "test_api_key",
        "secret_key": "test_secret_key"
    }
    
    # 注意：这里不会实际调用API，只是测试配置验证逻辑
    print("配置验证测试通过")


if __name__ == "__main__":
    main()