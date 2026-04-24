import sys
from pathlib import Path

# 讓 src 套件可被 import（無論從哪個目錄執行）
sys.path.insert(0, str(Path(__file__).parent))

try:
    import tkinterdnd2 as dnd  # noqa: F401
    _has_dnd = True
except ImportError:
    _has_dnd = False

from src.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
