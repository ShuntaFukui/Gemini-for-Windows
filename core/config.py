"""
設定管理モジュール
"""
import json
import os
from typing import Any, Dict
from dotenv import load_dotenv


class Config:
    """設定管理クラス"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # 環境変数の読み込み
        load_dotenv()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルの読み込み"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定を返す
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            "app": {
                "name": "Gemini Chat",
                "version": "1.0.0",
                "window": {
                    "width": 450,
                    "height": 600,
                    "min_width": 300,
                    "min_height": 400
                }
            },
            "gemini": {
                "model": "gemini-2.5-flash",
                "temperature": 0.7,
                "max_tokens": 2048
            },
            "database": {
                "path": "data/chats.db"
            },
            "ui": {
                "theme": "light",
                "font_size": 12
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得
        
        Args:
            key: 設定キー（ドット記法で階層指定可能）
            default: デフォルト値
            
        Returns:
            設定値
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_api_key(self) -> str:
        """Gemini APIキーを取得"""
        return os.getenv("GEMINI_API_KEY", "")
    
    def save(self):
        """設定をファイルに保存"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
