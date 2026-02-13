"""
システムトレイアイコンモジュール
"""
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtCore import QSize


class TrayIcon(QSystemTrayIcon):
    """システムトレイアイコンクラス"""
    
    def __init__(self, main_window):
        """
        初期化
        
        Args:
            main_window: メインウィンドウインスタンス
        """
        super().__init__(main_window)
        
        # カスタムアイコンを読み込み
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon", "icon.png")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            # アイコンファイルが存在しない場合はデフォルトアイコンを使用
            style = QApplication.style()
            if style:
                icon = style.standardIcon(style.StandardPixmap.SP_MessageBoxInformation)
            else:
                icon = QIcon()
        
        self.setIcon(icon)
        
        self.main_window = main_window
        self._create_menu()
        
        # トレイアイコンのクリックイベント
        self.activated.connect(self._on_activated)
    
    def _create_menu(self):
        """コンテキストメニューの作成"""
        menu = QMenu()
        
        # ウィンドウを開く
        show_action = QAction("開く", self)
        show_action.triggered.connect(self.main_window.show_window)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # 新しいチャット
        new_chat_action = QAction("新しいチャット", self)
        new_chat_action.triggered.connect(self._on_new_chat)
        menu.addAction(new_chat_action)
        
        menu.addSeparator()
        
        # 終了
        quit_action = QAction("終了", self)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
    
    def _on_activated(self, reason):
        """
        トレイアイコンがクリックされた時の処理
        
        Args:
            reason: アクティベーションの理由
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 左クリック
            self.main_window.show_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # ダブルクリック
            self.main_window.show_window()
    
    def _on_new_chat(self):
        """新しいチャットを作成"""
        self.main_window.show_window()
        self.main_window.create_new_chat()
    
    def _on_quit(self):
        """アプリケーションを終了"""
        self.main_window.close()
        QApplication.quit()
