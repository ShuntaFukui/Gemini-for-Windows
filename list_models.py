"""
利用可能なGemini APIモデルをリスト
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    
    print("=== 利用可能なGemini APIモデル ===\n")
    
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"モデル名: {model.name}")
            print(f"  表示名: {model.display_name}")
            print(f"  説明: {model.description}")
            print(f"  対応メソッド: {', '.join(model.supported_generation_methods)}")
            print()
else:
    print("エラー: GEMINI_API_KEYが設定されていません")
