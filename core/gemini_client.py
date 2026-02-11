"""
Gemini APIクライアントモジュール
"""
import google.generativeai as genai
from typing import Optional, Generator


class GeminiClient:
    """Gemini APIクライアントクラス"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        初期化
        
        Args:
            api_key: Gemini APIキー
            model_name: 使用するモデル名
        """
        self.api_key = api_key
        self.model_name = model_name
        self._configure()
    
    def _configure(self):
        """APIの設定"""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
    
    def generate_response(self, prompt: str, stream: bool = False) -> str:
        """
        レスポンスを生成
        
        Args:
            prompt: プロンプト
            stream: ストリーミングモードを使用するかどうか
            
        Returns:
            生成されたレスポンス
        """
        try:
            if stream:
                return self._generate_stream(prompt)
            else:
                response = self.model.generate_content(prompt)
                return response.text
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"
    
    def _generate_stream(self, prompt: str) -> Generator[str, None, None]:
        """
        ストリーミングでレスポンスを生成
        
        Args:
            prompt: プロンプト
            
        Yields:
            生成されたテキストの断片
        """
        try:
            response = self.model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"エラーが発生しました: {str(e)}"
    
    def generate_chat_response(self, chat_history: list, user_message: str) -> str:
        """
        チャット履歴を考慮してレスポンスを生成
        
        Args:
            chat_history: チャット履歴 [{"role": "user/assistant", "content": "..."}]
            user_message: ユーザーの新しいメッセージ
            
        Returns:
            生成されたレスポンス
        """
        try:
            # チャット履歴を含むプロンプトを構築
            conversation = []
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                conversation.append({"role": role, "parts": [msg["content"]]})
            
            # チャットセッションの開始
            chat = self.model.start_chat(history=conversation)
            response = chat.send_message(user_message)
            
            return response.text
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"
