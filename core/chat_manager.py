"""
チャット管理モジュール
"""
import uuid
from typing import List, Dict, Optional
from .database import Database
from .gemini_client import GeminiClient


class ChatManager:
    """チャット管理クラス"""
    
    def __init__(self, database: Database, gemini_client: GeminiClient):
        """
        初期化
        
        Args:
            database: データベースインスタンス
            gemini_client: Gemini APIクライアント
        """
        self.db = database
        self.gemini = gemini_client
    
    def create_new_chat(self, title: str = "新しいチャット") -> str:
        """
        新しいチャットを作成
        
        Args:
            title: チャットのタイトル
            
        Returns:
            作成されたチャットのID
        """
        chat_id = str(uuid.uuid4())
        self.db.create_conversation(chat_id, title)
        return chat_id
    
    def get_all_chats(self) -> List[Dict]:
        """
        全てのチャットを取得
        
        Returns:
            チャットのリスト
        """
        return self.db.get_conversations()
    
    def get_chat_messages(self, chat_id: str) -> List[Dict]:
        """
        特定のチャットのメッセージを取得
        
        Args:
            chat_id: チャットID
            
        Returns:
            メッセージのリスト
        """
        return self.db.get_messages(chat_id)
    
    def send_message(self, chat_id: str, user_message: str) -> str:
        """
        メッセージを送信し、レスポンスを取得
        
        Args:
            chat_id: チャットID
            user_message: ユーザーのメッセージ
            
        Returns:
            Geminiのレスポンス
        """
        # ユーザーメッセージを保存
        self.db.add_message(chat_id, "user", user_message)
        
        # チャット履歴を取得
        chat_history = self.db.get_messages(chat_id)
        
        # Gemini APIでレスポンスを生成
        response = self.gemini.generate_chat_response(chat_history[:-1], user_message)
        
        # アシスタントのレスポンスを保存
        self.db.add_message(chat_id, "assistant", response)
        
        return response
    
    def delete_chat(self, chat_id: str) -> bool:
        """
        チャットを削除
        
        Args:
            chat_id: チャットID
            
        Returns:
            成功した場合True
        """
        return self.db.delete_conversation(chat_id)
    
    def update_chat_title(self, chat_id: str, title: str) -> bool:
        """
        チャットのタイトルを更新
        
        Args:
            chat_id: チャットID
            title: 新しいタイトル
            
        Returns:
            成功した場合True
        """
        return self.db.update_conversation_title(chat_id, title)
