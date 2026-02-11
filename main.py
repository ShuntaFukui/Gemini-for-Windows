"""
Gemini Chat - Windows常駐型チャットアプリケーション
メインエントリーポイント
"""
import sys
import signal
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.tray_icon import TrayIcon
from ui.main_window import MainWindow
from core.database import Database


def main():
    """アプリケーションのメインエントリーポイント"""
    # アプリケーションの初期化
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # ウィンドウを閉じてもアプリは終了しない
    
    # Ctrl+Cで終了できるようにする
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # Pythonがシグナルを処理できるようにタイマーを設定
    timer = QTimer()
    timer.start(500)  # 500msごとにPythonインタープリタを起動
    timer.timeout.connect(lambda: None)
    
    # データベースの初期化
    db = Database()
    db.initialize()
    
    # メインウィンドウの作成
    main_window = MainWindow()
    
    # システムトレイアイコンの作成
    tray_icon = TrayIcon(main_window)
    tray_icon.show()
    
    # アプリケーションの実行
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
