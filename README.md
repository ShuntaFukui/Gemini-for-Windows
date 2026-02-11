# Gemini Chat - Windows常駐型アプリケーション

Gemini APIを使用したWindows常駐型チャットアプリケーション。タスクトレイに常駐し、複数のチャット履歴を管理できます。

## 機能

- **タスクトレイ常駐**: システムトレイからワンクリックでアクセス
- **複数チャット管理**: 複数の会話を並行して管理可能
- **チャット履歴永続化**: SQLiteデータベースで履歴を保存
- **Markdown対応**: Geminiの応答をMarkdown形式で表示
- **モデル選択**: 複数のGeminiモデルから選択可能
- **モダンUI**: 白ベースの洗練されたデザイン

## 必要要件

- **Python 3.9以上**（推奨・動作確認: Python 3.13）
- **Gemini API キー**（[Google AI Studio](https://makersuite.google.com/app/apikey)で取得）
- **Windows 10/11**
- **インターネット接続**（Gemini API通信用）

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/gamini.git
cd gamini
```

### 2. Python仮想環境の作成

```bash
# 仮想環境の作成
python -m venv .venv

# 仮想環境のアクティベート（PowerShell）
.venv\Scripts\Activate.ps1

# 仮想環境のアクティベート（コマンドプロンプト）
.venv\Scripts\activate.bat
```

**注意**: PowerShellで実行ポリシーエラーが出る場合:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

**インストールされるパッケージ**:
- `PyQt6` (6.6.1): GUIフレームワーク
- `google-generativeai` (0.3.2): Gemini API SDK
- `markdown` (3.5.1): Markdown→HTML変換
- `cryptography` (42.0.0): APIキー暗号化
- `python-dotenv` (1.0.0): 環境変数管理

### 4. 環境変数の設定

```bash
# .env.exampleをコピー
copy .env.example .env
```

`.env`ファイルを開き、Gemini APIキーを設定:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

**APIキーの取得方法**:
1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
2. Googleアカウントでログイン
3. 「Create API Key」をクリック
4. 生成されたキーをコピーして`.env`に貼り付け

### 5. アプリケーションの起動

```bash
python main.py
```

初回起動時、以下が自動的に作成されます:
- `data/chats.db`: チャット履歴データベース
- システムトレイアイコン

## 使い方

### 基本操作

1. **アプリケーション起動**: タスクトレイにアイコンが表示されます
2. **チャット画面を開く**: トレイアイコンをクリック
3. **メッセージ送信**:
   - テキストを入力
   - `Ctrl+Enter`で送信（`Enter`のみは改行）
4. **新しいチャット作成**: サイドバーの「+ 新しいチャット」ボタン
5. **モデル変更**: サイドバーのプルダウンから選択

### 利用可能なモデル

- `gemini-2.5-flash`: 高速・低コスト（デフォルト）
- `gemini-2.5-pro`: 高性能
- `gemini-2.0-flash`: 第2世代・高速
- `gemini-2.0-flash-lite`: 超軽量版
- `gemini-3-flash-preview`: 第3世代プレビュー（高速）
- `gemini-3-pro-preview`: 第3世代プレビュー（高性能）

### キーボードショートカット

- `Enter`: 改行
- `Ctrl+Enter`: メッセージ送信

## トラブルシューティング

### APIキーエラー

```
Error: API key not valid
```

**解決方法**:
1. `.env`ファイルが存在するか確認
2. APIキーが正しいか確認
3. APIキーに余分なスペースがないか確認

### モジュールが見つからないエラー

```
ModuleNotFoundError: No module named 'PyQt6'
```

**解決方法**:
```bash
# 仮想環境がアクティブか確認
# プロンプトに(.venv)が表示されているはず

# 再インストール
pip install -r requirements.txt
```

### データベースエラー

データベースが破損した場合:
```bash
# データベースファイルを削除（履歴は失われます）
del data\chats.db

# アプリケーションを再起動すると自動で再作成されます
python main.py
```

## プロジェクト構造

```
gamini/
├── main.py              # エントリーポイント
├── ui/                  # UI関連
│   ├── main_window.py   # メインチャット画面
│   ├── tray_icon.py     # システムトレイアイコン
│   └── chat_widget.py   # チャットウィジェット
├── core/                # コアロジック
│   ├── gemini_client.py # Gemini API クライアント
│   ├── chat_manager.py  # チャット管理
│   ├── database.py      # データベース管理
│   └── config.py        # 設定管理
├── resources/           # リソースファイル
│   └── icon.ico         # アプリケーションアイコン
├── data/                # データファイル (gitignore)
│   └── chats.db         # SQLiteデータベース
└── requirements.txt     # 依存関係
```
