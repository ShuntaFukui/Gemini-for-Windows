"""
データベース管理モジュール
チャット履歴をSQLiteで永続化
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional


class Database:
    """SQLiteデータベース管理クラス"""
    
    def __init__(self, db_path: str = "data/chats.db"):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """データディレクトリの存在を確認、なければ作成"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def initialize(self):
        """データベーステーブルの初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 会話テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # メッセージテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_conversation(self, conversation_id: str, title: str = "新しいチャット") -> bool:
        """
        新しい会話を作成
        
        Args:
            conversation_id: 会話ID
            title: 会話のタイトル
            
        Returns:
            成功した場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (id, title) VALUES (?, ?)",
                (conversation_id, title)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def get_conversations(self) -> List[Dict]:
        """
        全ての会話を取得
        
        Returns:
            会話のリスト
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def add_message(self, conversation_id: str, role: str, content: str) -> bool:
        """
        メッセージを追加
        
        Args:
            conversation_id: 会話ID
            role: 'user' または 'assistant'
            content: メッセージ内容
            
        Returns:
            成功した場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content)
            )
            # 会話の更新日時を更新
            cursor.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def get_messages(self, conversation_id: str) -> List[Dict]:
        """
        特定の会話のメッセージを取得
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            メッセージのリスト
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conversation_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        会話を削除
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            成功した場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """
        会話のタイトルを更新
        
        Args:
            conversation_id: 会話ID
            title: 新しいタイトル
            
        Returns:
            成功した場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, conversation_id)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
