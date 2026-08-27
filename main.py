import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# 讓 src 套件可被 import（無論從哪個目錄執行）
sys.path.insert(0, str(Path(__file__).parent))

from src.app import MainWindow

if __name__ == "__main__":
    # PySide6/Qt6 預設已內建良好的高 DPI 支援
    app = QApplication(sys.argv)
    
    # 設定應用程式名稱
    app.setApplicationName("NotebookLM 檔案切分工具")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
