"""
メインウィンドウモジュール
"""
import re
import markdown
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QTextEdit, QLineEdit, QTabWidget,
                              QListWidget, QSplitter, QLabel, QComboBox, QPlainTextEdit,
                              QToolButton, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, QRect, QTimer
from PyQt6.QtGui import QTextCursor, QKeyEvent, QFontMetrics, QIcon
from core.config import Config
from core.database import Database
from core.gemini_client import GeminiClient
from core.chat_manager import ChatManager


class GeminiWorker(QThread):
    """Gemini API呼び出し用のワーカースレッド"""
    
    # レスポンス受信時のシグナル（chat_idも含める）
    response_received = pyqtSignal(int, str)
    # エラー発生時のシグナル（chat_idも含める）
    error_occurred = pyqtSignal(int, str)
    
    def __init__(self, chat_manager, chat_id: int, message: str):
        super().__init__()
        self.chat_manager = chat_manager
        self.chat_id = chat_id
        self.message = message
    
    def run(self):
        """APIを呼び出してレスポンスを取得"""
        try:
            response = self.chat_manager.send_message(self.chat_id, self.message)
            self.response_received.emit(self.chat_id, response)
        except Exception as e:
            self.error_occurred.emit(self.chat_id, str(e))


class MultiLineInput(QPlainTextEdit):
    """複数行入力対応のカスタムテキスト入力ウィジェット"""
    
    send_message = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("メッセージを入力... (Ctrl+Enterで送信)")
        
        # 初期高さを1行に設定
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 行の高さを計算
        self.line_height = QFontMetrics(self.font()).lineSpacing()
        self.setMinimumHeight(self._calculate_height(1))
        self.setMaximumHeight(self._calculate_height(5))
        
        # テキスト変更時に高さを調整
        self.textChanged.connect(self._adjust_height)
        
        # 初期高さを設定
        self._adjust_height()
        
    def _calculate_height(self, lines: int) -> int:
        """指定された行数の高さを計算"""
        # コンテンツマージンとパディングを考慮
        margins = self.contentsMargins()
        frame_width = self.frameWidth()
        extra_height = margins.top() + margins.bottom() + frame_width * 2 + 10
        return self.line_height * lines + extra_height
    
    def _adjust_height(self):
        """テキストの行数に応じて高さを調整"""
        # 実際の行数を取得
        line_count = self.document().blockCount()
        
        # 空の場合は1行として扱う
        if line_count == 0:
            line_count = 1
        
        # 最小1行、最大5行
        display_lines = max(1, min(5, line_count))
        
        # 高さを設定
        new_height = self._calculate_height(display_lines)
        self.setFixedHeight(new_height)
        
        # 5行を超えた場合はスクロールバーを表示
        if line_count > 5:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
    
    def keyPressEvent(self, event: QKeyEvent):
        """キーイベントの処理"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Enter で送信
                self.send_message.emit()
                event.accept()
                return
            else:
                # Enter で改行
                super().keyPressEvent(event)
                return
        
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    def __init__(self):
        """初期化"""
        super().__init__()
        
        # 設定の読み込み
        self.config = Config()
        
        # データベースとAPIクライアントの初期化
        self.db = Database(self.config.get("database.path"))
        
        api_key = self.config.get_api_key()
        if not api_key:
            # APIキーが設定されていない場合、後で設定できるようにする
            api_key = "dummy_key"  # 仮のキー
        
        self.gemini = GeminiClient(api_key, self.config.get("gemini.model"))
        self.chat_manager = ChatManager(self.db, self.gemini)
        
        # 現在のチャットID
        self.current_chat_id = None
        
        # サイドバーの表示状態
        self.sidebar_visible = False
        
        # メッセージバッファ（現在表示中のメッセージHTMLを保持）
        self.messages_html = []
        
        # ローディングアニメーション用
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self._update_loading_animation)
        self.loading_dots = 0
        self.loading_message_index = None
        
        # ワーカースレッド
        self.worker = None
        
        # UIの初期化
        self._init_ui()
        self._load_chats()
    
    def _init_ui(self):
        """UIの初期化"""
        self.setWindowTitle(self.config.get("app.name"))
        self.resize(
            self.config.get("app.window.width"),
            self.config.get("app.window.height")
        )
        
        # Markdownレンダラーの設定
        self.md = markdown.Markdown(extensions=['fenced_code', 'codehilite', 'tables', 'nl2br'])
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # サイドバー（引き出し）
        self.sidebar = self._create_sidebar()
        self.sidebar.setFixedWidth(150)
        main_layout.addWidget(self.sidebar)
        
        # チャットエリア用のコンテナ
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)
        
        # ハンバーガーメニューボタン用のヘッダー
        header = QWidget()
        header.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #f0f0f0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        # ハンバーガーメニューボタン
        self.menu_button = QToolButton()
        self.menu_button.setText("☰")
        self.menu_button.setStyleSheet("""
            QToolButton {
                font-size: 20px;
                border: none;
                background-color: transparent;
                padding: 8px;
                color: #666;
            }
            QToolButton:hover {
                background-color: #f5f5f5;
                border-radius: 8px;
            }
        """)
        self.menu_button.setFixedSize(36, 36)
        self.menu_button.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.menu_button)
        
        header_layout.addStretch()
        chat_layout.addWidget(header)
        
        # チャットエリア
        chat_area = self._create_chat_area()
        chat_layout.addWidget(chat_area)
        
        main_layout.addWidget(chat_container)
    
    def _create_sidebar(self) -> QWidget:
        """サイドバーを作成"""
        sidebar = QFrame()
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-right: 1px solid #e8e8e8;
            }
        """)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # モデル選択
        model_label = QLabel("モデル")
        model_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.model_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #ffffff;
                font-size: 13px;
                color: #333;
                font-weight: 500;
            }
            QComboBox:hover {
                border-color: #667eea;
                background-color: #fafafa;
            }
            QComboBox:focus {
                border-color: #667eea;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
                background: transparent;
            }
            QComboBox::drop-down:hover {
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #667eea;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
                outline: none;
                selection-background-color: #e8eaf6;
                selection-color: #667eea;
                font-size: 13px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px 0;
                min-height: 20px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #f5f5f5;
                color: #333;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #e8eaf6;
                color: #667eea;
                font-weight: 600;
            }
        """)
        self.model_combo.addItems([
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3-pro-preview"
        ])
        
        # プルダウンリストの幅を最も長いアイテムに合わせる
        max_width = 0
        fm = self.model_combo.fontMetrics()
        for i in range(self.model_combo.count()):
            text = self.model_combo.itemText(i)
            # horizontalAdvance を使用してより正確な幅を取得
            if hasattr(fm, 'horizontalAdvance'):
                width = fm.horizontalAdvance(text)
            else:
                width = fm.boundingRect(text).width()
            max_width = max(max_width, width)
        # パディング、マージン、スクロールバー用のスペースを十分に追加
        self.model_combo.view().setMinimumWidth(max_width + 60)
        
        # 現在のモデルを選択
        current_model = self.config.get("gemini.model")
        index = self.model_combo.findText(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self.model_combo)
        
        layout.addSpacing(8)
        
        # 新しいチャットボタン
        self.new_chat_btn = QPushButton("+ 新しいチャット")
        self.new_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #afeeee;
                color: #666;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #b0e0e6;
            }
            QPushButton:pressed {
                background-color: #add8e6;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #999;
            }
        """)
        self.new_chat_btn.clicked.connect(self.create_new_chat)
        layout.addWidget(self.new_chat_btn)
        
        # チャットリスト
        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                border-radius: 8px;
                padding: 10px 12px;
                margin: 2px 0;
                color: #333;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
            QListWidget::item:selected {
                background-color: #e8eaf6;
                color: #667eea;
            }
        """)
        self.chat_list.itemClicked.connect(self._on_chat_selected)
        layout.addWidget(self.chat_list)
        
        return sidebar
    
    def _toggle_sidebar(self):
        """サイドバーの表示/非表示を切り替え"""
        if self.sidebar_visible:
            # サイドバーを非表示
            self.sidebar.hide()
            self.sidebar_visible = False
        else:
            # サイドバーを表示
            self.sidebar.show()
            self.sidebar_visible = True
    
    def _create_chat_area(self) -> QWidget:
        """チャットエリアを作成"""
        chat_area = QWidget()
        layout = QVBoxLayout(chat_area)
        
        # チャット表示エリア
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        # カスタムスタイルシートを適用
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: none;
                padding: 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # 入力エリア
        input_layout = QHBoxLayout()
        
        self.message_input = MultiLineInput()
        self.message_input.send_message.connect(self._send_message)
        input_layout.addWidget(self.message_input)
        
        send_btn = QPushButton("送信")
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #afeeee;
                color: #666;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #b0e0e6;
            }
            QPushButton:pressed {
                background-color: #add8e6;
            }
        """)
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        return chat_area
    
    def _load_chats(self):
        """チャットリストを読み込み"""
        self.chat_list.clear()
        chats = self.chat_manager.get_all_chats()
        
        for chat in chats:
            self.chat_list.addItem(chat["title"])
            # チャットIDをアイテムのデータとして保存
            item = self.chat_list.item(self.chat_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, chat["id"])
    
    def _refresh_chat_list(self):
        """チャットリストを更新（現在の選択を維持）"""
        current_id = self.current_chat_id
        self._load_chats()
        
        # 現在のチャットを再選択
        if current_id:
            for i in range(self.chat_list.count()):
                item = self.chat_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == current_id:
                    self.chat_list.setCurrentItem(item)
                    break
    
    def _on_chat_selected(self, item):
        """チャットが選択された時の処理"""
        # 応答待機中はチャット切り替えを禁止
        if self.worker and self.worker.isRunning():
            # 前のチャットに戻す
            for i in range(self.chat_list.count()):
                list_item = self.chat_list.item(i)
                if list_item.data(Qt.ItemDataRole.UserRole) == self.current_chat_id:
                    self.chat_list.setCurrentItem(list_item)
                    break
            return
        
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_chat_id = chat_id
        self._load_messages(chat_id)
    
    def _load_messages(self, chat_id: str):
        """メッセージを読み込み"""
        self.chat_display.clear()
        self.messages_html = []
        
        messages = self.chat_manager.get_chat_messages(chat_id)
        
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            role_label = "あなた" if msg["role"] == "user" else "Gemini"
            
            # MarkdownをHTMLに変換
            if role == "assistant":
                content_html = self.md.convert(msg['content'])
                self.md.reset()
            else:
                # ユーザーメッセージはプレーンテキスト
                content_html = msg['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            
            # HTMLタグにinline styleを追加してmarginを削除
            content_html = re.sub(r'<(ul|ol)>', r'<\1 style="margin:0 !important;padding:0 !important;margin-left:20px !important;">', content_html)
            content_html = re.sub(r'<li>', '<li style="margin:0 !important;padding:0 !important;line-height:1.2 !important;">', content_html)
            content_html = re.sub(r'<(h[1-6])>', r'<\1 style="margin:0;padding:0;">', content_html)
            # pタグを削除してbrタグに置き換え（QTextEditの制限回避）
            content_html = re.sub(r'<p[^>]*>', '', content_html)
            content_html = re.sub(r'</p>', '<br>', content_html)
            # 連続するbrタグを1つにまとめる
            content_html = re.sub(r'(<br>\s*){2,}', '<br>', content_html)
            # 末尾の余分なbrタグを削除
            content_html = re.sub(r'(<br>\s*)+$', '', content_html)
            # 先頭の余分なbrタグも削除
            content_html = re.sub(r'^\s*(<br>\s*)+', '', content_html)
            
            # メッセージHTMLを作成して追加（可変幅版）
            if role == "user":
                align = "right"
                bg_color = "#fce4ec"
                border_color = "#f8bbd0"
            else:
                align = "left"
                bg_color = "#e0f7fa"
                border_color = "#b2ebf2"
            
            message_html = f"""
<div style="clear: both; margin: 4px 0; text-align: {align};">
<table cellpadding="0" cellspacing="0" style="display: inline-table; max-width: 75%; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; border-collapse: separate;">
<tr>
<td style="padding: 8px 12px;">
<div style="color: #333; line-height: 1.2; text-align: left;">{content_html}</div>
</td>
</tr>
</table>
</div>
"""
            self.messages_html.append(message_html)
        
        # 全てのメッセージを表示
        self._render_messages()
    
    def _send_message(self):
        """メッセージを送信"""
        if not self.current_chat_id:
            # チャットが選択されていない場合、新規作成
            self.create_new_chat()
        
        message = self.message_input.toPlainText().strip()
        if not message:
            return
        
        # 送信中は入力を無効化
        self.message_input.setEnabled(False)
        # チャット切り替えと新規作成を禁止
        self.chat_list.setEnabled(False)
        self.new_chat_btn.setEnabled(False)
        
        # 入力欄をクリア
        self.message_input.clear()
        
        # ユーザーメッセージを画面に追加
        self._append_message_to_display("user", message, is_markdown=False)
        
        # ローディング表示を追加
        self._show_loading()
        
        # ワーカースレッドでAPIを呼び出し
        self.worker = GeminiWorker(self.chat_manager, self.current_chat_id, message)
        self.worker.response_received.connect(self._on_response_received)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()
    
    def _show_loading(self):
        """ローディングアニメーションを表示"""
        self.loading_dots = 0
        # ローディングメッセージを追加
        self._append_message_to_display("assistant", "...", is_markdown=False)
        # 最後に追加したメッセージのインデックスを記録
        self.loading_message_index = len(self.messages_html) - 1
        # アニメーション開始
        self.loading_timer.start(500)  # 500msごとに更新
    
    def _update_loading_animation(self):
        """ローディングアニメーションを更新"""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * (self.loading_dots if self.loading_dots > 0 else 1)
        
        # ローディングメッセージを更新
        if self.loading_message_index is not None:
            loading_html = f"""
<div style="clear: both; margin: 4px 0; text-align: left;">
<table cellpadding="0" cellspacing="0" style="display: inline-table; max-width: 75%; background-color: #e0f7fa; border: 1px solid #b2ebf2; border-radius: 8px; border-collapse: separate;">
<tr>
<td style="padding: 8px 12px;">
<div style="color: #666; line-height: 1.2; text-align: left; font-style: italic;">
応答を生成中{dots}
</div>
</td>
</tr>
</table>
</div>
"""
            self.messages_html[self.loading_message_index] = loading_html
            self._render_messages()
    
    def _on_response_received(self, chat_id: int, response: str):
        """レスポンス受信時の処理"""
        # 現在のチャットIDと一致しない場合は無視
        if chat_id != self.current_chat_id:
            return
        
        # ローディング状態をクリーンアップ
        self._stop_loading_animation()
        
        # Geminiのレスポンスを画面に追加
        self._append_message_to_display("assistant", response, is_markdown=True)
        
        # チャットリストを更新（タイトルが変更された可能性があるため）
        self._refresh_chat_list()
        
        # UIを再度有効化
        self._enable_ui()
    
    def _on_error_occurred(self, chat_id: int, error: str):
        """エラー発生時の処理"""
        # 現在のチャットIDと一致しない場合は無視
        if chat_id != self.current_chat_id:
            return
        
        # ローディング状態をクリーンアップ
        self._stop_loading_animation()
        
        # エラーメッセージを表示
        error_message = f"エラーが発生しました: {error}"
        self._append_message_to_display("assistant", error_message, is_markdown=False)
        
        # UIを再度有効化
        self._enable_ui()
        
        # UIを再度有効化
        self._enable_ui()
    
    def _on_worker_finished(self):
        """ワーカースレッド終了時の処理"""
        # sender()で現在のワーカーか確認
        sender = self.sender()
        if sender == self.worker:
            # UIを再度有効化
            self._enable_ui()
            
            # ワーカースレッドのクリーンアップ
            if self.worker:  # Noneチェック追加
                self.worker.deleteLater()
                self.worker = None
        elif sender:
            # キャンセルされた古いワーカー
            sender.deleteLater()
    
    def _enable_ui(self):
        """入力欄、チャットリスト、新規チャットボタンを有効化"""
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        self.chat_list.setEnabled(True)
        self.new_chat_btn.setEnabled(True)
    
    def _stop_loading_animation(self):
        """ローディングアニメーションを停止"""
        self.loading_timer.stop()
        
        # ローディングメッセージを削除
        if self.loading_message_index is not None and self.loading_message_index < len(self.messages_html):
            self.messages_html.pop(self.loading_message_index)
            self.loading_message_index = None
            self._render_messages()
    
    def _append_message_to_display(self, role: str, content: str, is_markdown: bool = False):
        """メッセージを画面に追加（既存のメッセージの下に追加）"""
        role_label = "あなた" if role == "user" else "Gemini"
        
        # Markdownの場合は変換
        if is_markdown:
            content_html = self.md.convert(content)
            self.md.reset()
        else:
            # プレーンテキストの場合はHTMLエスケープして改行を<br>に変換
            content_html = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        
        # HTMLタグにinline styleを追加してmarginを削除
        content_html = re.sub(r'<(ul|ol)>', r'<\1 style="margin:0 !important;padding:0 !important;margin-left:20px !important;">', content_html)
        content_html = re.sub(r'<li>', '<li style="margin:0 !important;padding:0 !important;line-height:1.2 !important;">', content_html)
        content_html = re.sub(r'<(h[1-6])>', r'<\1 style="margin:0;padding:0;">', content_html)
        # pタグを削除してbrタグに置き換え（QTextEditの制限回避）
        content_html = re.sub(r'<p[^>]*>', '', content_html)
        content_html = re.sub(r'</p>', '<br>', content_html)
        # 連続するbrタグを1つにまとめる
        content_html = re.sub(r'(<br>\s*){2,}', '<br>', content_html)
        # 末尾の余分なbrタグを削除
        content_html = re.sub(r'(<br>\s*)+$', '', content_html)
        # 先頭の余分なbrタグも削除
        content_html = re.sub(r'^\s*(<br>\s*)+', '', content_html)
        
        # メッセージHTMLを作成（可変幅版）
        if role == "user":
            align = "right"
            bg_color = "#fce4ec"
            border_color = "#f8bbd0"
        else:
            align = "left"
            bg_color = "#e0f7fa"
            border_color = "#b2ebf2"
        
        message_html = f"""
<div style="clear: both; margin: 4px 0; text-align: {align};">
<table cellpadding="0" cellspacing="0" style="display: inline-table; max-width: 75%; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; border-collapse: separate;">
<tr>
<td style="padding: 8px 12px;">
<div style="color: #333; line-height: 1.2; text-align: left;">
<style scoped>
p, ul, ol, h1, h2, h3, h4, h5, h6 {{ margin: 0 !important; padding: 0 !important; }}
ul, ol {{ padding-left: 20px !important; }}
</style>
{content_html}
</div>
</td>
</tr>
</table>
</div>
"""
        
        # メッセージバッファに追加
        self.messages_html.append(message_html)
        
        # 全てのメッセージを再レンダリング
        self._render_messages()
    
    def _render_messages(self):
        """全てのメッセージを画面に表示"""
        # 完全なHTMLドキュメントを構築
        full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    {self._get_chat_styles()}
</head>
<body>
    {''.join(self.messages_html)}
</body>
</html>
"""
        
        # デバッグ用：HTMLをファイルに出力
        try:
            with open('debug_output.html', 'w', encoding='utf-8') as f:
                f.write(full_html)
            print(f"HTMLを debug_output.html に出力しました。メッセージ数: {len(self.messages_html)}")
        except Exception as e:
            print(f"HTML出力エラー: {e}")
        
        # HTMLを設定
        self.chat_display.setHtml(full_html)
        
        # 自動スクロール
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
    
    def create_new_chat(self):
        """新しいチャットを作成"""
        # 応答待機中は新規チャット作成を禁止
        if self.worker and self.worker.isRunning():
            return
        
        chat_id = self.chat_manager.create_new_chat()
        self.current_chat_id = chat_id
        self._load_chats()
        
        # チャット表示をクリア
        self.chat_display.clear()
        self.messages_html = []
        self._render_messages()
        
        # 新しいチャットを選択
        last_item = self.chat_list.item(0)
        if last_item:
            self.chat_list.setCurrentItem(last_item)

    def _on_model_changed(self, model_name: str):
        """モデルが変更された時の処理"""
        # GeminiClientを再初期化
        api_key = self.config.get_api_key()
        if api_key:
            self.gemini = GeminiClient(api_key, model_name)
            self.chat_manager.gemini = self.gemini
            
            # 設定を更新
            if "gemini" not in self.config.config:
                self.config.config["gemini"] = {}
            self.config.config["gemini"]["model"] = model_name
            
            # ステータス表示（オプション）
            print(f"モデルを {model_name} に変更しました")
    
    def _get_chat_styles(self) -> str:
        """チャット表示用のCSSスタイルを取得"""
        return """<style>
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #333;
    margin: 0;
    padding: 20px;
    background-color: #fafafa;
}
.message {
    margin: 4px 0;
    clear: both;
    width: 100%;
}
.message-bubble {
    max-width: 75%;
    padding: 16px 20px;
    border-radius: 12px;
    word-wrap: break-word;
}
.user-message .message-bubble {
    background-color: #fce4ec;
    border: 1px solid #f8bbd0;
    float: right;
}
.assistant-message .message-bubble {
    background-color: #e0f7fa;
    border: 1px solid #b2ebf2;
    float: left;
}
.message-header {
    font-weight: 600;
    margin-bottom: 10px;
    font-size: 12px;
}
.user-header {
    color: #c2185b;
}
.assistant-header {
    color: #0097a7;
}
.message-content {
    color: #333;
}
.message-bubble p {
    margin: 8px 0;
    padding: 0;
    color: #333;
}
.message-bubble p:first-child {
    margin-top: 0;
}
.message-bubble p:last-child {
    margin-bottom: 0;
}
pre {
    background-color: #263238;
    color: #aed581;
    padding: 12px;
    border-radius: 6px;
    margin: 12px 0;
}
code {
    background-color: rgba(0,0,0,0.08);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    color: #333;
}
pre code {
    background-color: transparent;
    padding: 0;
    color: #aed581;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
}
th, td {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: left;
    color: #333;
}
th {
    background-color: #f0f0f0;
    font-weight: bold;
}
blockquote {
    border-left: 4px solid #999;
    margin: 12px 0;
    padding-left: 15px;
    color: #555;
}
h1, h2, h3, h4, h5, h6 {
    margin-top: 16px;
    margin-bottom: 8px;
    color: #333;
}
ul, ol {
    margin: 10px 0;
    padding-left: 30px;
    color: #333;
}
li {
    margin: 4px 0;
    color: #333;
}
a {
    color: #1976d2;
    text-decoration: none;
}
</style>"""
    
    def show_window(self):
        """ウィンドウを表示"""
        self.show()
        self.activateWindow()
        self.raise_()
    
    def closeEvent(self, event):
        """ウィンドウが閉じられる時の処理"""
        # ウィンドウを隠すだけで終了しない
        event.ignore()
        self.hide()
