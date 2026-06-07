"""
凭证安全管理模块
使用系统密钥库加密存储敏感信息
"""
import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

# 尝试导入cryptography，如果不可用则使用简单加密
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class SimpleEncryption:
    """简单的XOR加密（当cryptography不可用时使用）"""
    
    def __init__(self, key: bytes):
        self.key = key
    
    def encrypt(self, data: bytes) -> bytes:
        result = bytearray()
        for i, byte in enumerate(data):
            result.append(byte ^ self.key[i % len(self.key)])
        return base64.b64encode(bytes(result))
    
    def decrypt(self, data: bytes) -> bytes:
        decoded = base64.b64decode(data)
        result = bytearray()
        for i, byte in enumerate(decoded):
            result.append(byte ^ self.key[i % len(self.key)])
        return bytes(result)


class CredentialManager:
    """凭证安全管理器"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".pyscreenshot"
        self.credentials_file = self.config_dir / "credentials.enc"
        self.key_file = self.config_dir / ".key"
        self._encryptor = None
        self._init_encryption()
    
    def _init_encryption(self):
        """初始化加密系统"""
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 获取或生成机器唯一标识作为盐
        machine_id = self._get_machine_id()
        
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # 生成新密钥
            key = self._derive_key(machine_id)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # 设置文件权限（仅限当前用户）
            if os.name != 'nt':
                os.chmod(self.key_file, 0o600)
        
        if HAS_CRYPTOGRAPHY:
            self._encryptor = Fernet(key)
        else:
            # 使用简单加密作为备用
            self._encryptor = SimpleEncryption(key)
    
    def _get_machine_id(self) -> bytes:
        """获取机器唯一标识"""
        import platform
        import uuid
        
        # 组合多个系统信息生成唯一标识
        info = f"{platform.node()}-{uuid.getnode()}-{os.getlogin()}"
        return hashlib.sha256(info.encode()).digest()
    
    def _derive_key(self, salt: bytes) -> bytes:
        """从盐派生加密密钥"""
        if HAS_CRYPTOGRAPHY:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt[:16],
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(salt))
        else:
            # 简单密钥派生
            key = hashlib.pbkdf2_hmac('sha256', salt, salt[:16], 100000)
            key = base64.urlsafe_b64encode(key)
        return key
    
    def _load_credentials(self) -> Dict[str, Any]:
        """加载凭证数据"""
        if not self.credentials_file.exists():
            return {}
        
        try:
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = self._encryptor.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception:
            return {}
    
    def _save_credentials(self, credentials: Dict[str, Any]):
        """保存凭证数据"""
        try:
            data = json.dumps(credentials, ensure_ascii=False).encode('utf-8')
            encrypted_data = self._encryptor.encrypt(data)
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
        except Exception as e:
            print(f"保存凭证失败: {e}")
    
    # FTP服务器凭证
    def save_ftp_server(self, name: str, host: str, port: int, 
                        username: str, password: str, path: str = "/"):
        """保存FTP服务器配置"""
        credentials = self._load_credentials()
        if 'ftp_servers' not in credentials:
            credentials['ftp_servers'] = {}
        
        credentials['ftp_servers'][name] = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'path': path
        }
        self._save_credentials(credentials)
    
    def get_ftp_server(self, name: str) -> Optional[Dict]:
        """获取FTP服务器配置"""
        credentials = self._load_credentials()
        return credentials.get('ftp_servers', {}).get(name)
    
    def get_all_ftp_servers(self) -> Dict[str, Dict]:
        """获取所有FTP服务器配置"""
        credentials = self._load_credentials()
        return credentials.get('ftp_servers', {})
    
    def delete_ftp_server(self, name: str):
        """删除FTP服务器配置"""
        credentials = self._load_credentials()
        if 'ftp_servers' in credentials and name in credentials['ftp_servers']:
            del credentials['ftp_servers'][name]
            self._save_credentials(credentials)
    
    # 云存储凭证
    def save_cloud_token(self, provider: str, token_data: Dict):
        """保存云存储OAuth令牌"""
        credentials = self._load_credentials()
        if 'cloud_tokens' not in credentials:
            credentials['cloud_tokens'] = {}
        
        credentials['cloud_tokens'][provider] = token_data
        self._save_credentials(credentials)
    
    def get_cloud_token(self, provider: str) -> Optional[Dict]:
        """获取云存储OAuth令牌"""
        credentials = self._load_credentials()
        return credentials.get('cloud_tokens', {}).get(provider)
    
    def delete_cloud_token(self, provider: str):
        """删除云存储令牌"""
        credentials = self._load_credentials()
        if 'cloud_tokens' in credentials and provider in credentials['cloud_tokens']:
            del credentials['cloud_tokens'][provider]
            self._save_credentials(credentials)
    
    # 社交账号凭证
    def save_social_token(self, platform: str, token_data: Dict):
        """保存社交平台OAuth令牌"""
        credentials = self._load_credentials()
        if 'social_tokens' not in credentials:
            credentials['social_tokens'] = {}
        
        credentials['social_tokens'][platform] = token_data
        self._save_credentials(credentials)
    
    def get_social_token(self, platform: str) -> Optional[Dict]:
        """获取社交平台OAuth令牌"""
        credentials = self._load_credentials()
        return credentials.get('social_tokens', {}).get(platform)
    
    def delete_social_token(self, platform: str):
        """删除社交平台令牌"""
        credentials = self._load_credentials()
        if 'social_tokens' in credentials and platform in credentials['social_tokens']:
            del credentials['social_tokens'][platform]
            self._save_credentials(credentials)
    
    # 最近使用的目录
    def save_recent_path(self, provider: str, path: str):
        """保存最近使用的上传目录"""
        credentials = self._load_credentials()
        if 'recent_paths' not in credentials:
            credentials['recent_paths'] = {}
        
        credentials['recent_paths'][provider] = path
        self._save_credentials(credentials)
    
    def get_recent_path(self, provider: str) -> str:
        """获取最近使用的上传目录"""
        credentials = self._load_credentials()
        return credentials.get('recent_paths', {}).get(provider, "/")


# 全局实例
_credential_manager = None

def get_credential_manager() -> CredentialManager:
    """获取凭证管理器单例"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
