import sys
import os
from pathlib import Path
import platform

# 在建立任何 GUI 元件前，於 Windows 上設定 DPI-awareness，避免顯示模糊
if platform.system() == "Windows":
    try:
        import ctypes
        # 優先使用 Windows 10+ 的 API
        try:
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4  # per-monitor v2
            ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        except Exception:
            try:
                # Windows 8.1+: SetProcessDpiAwareness
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
            except Exception:
                try:
                    # 舊的備援 API
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
    except Exception:
        pass

    # 依系統 DPI 設定 tkinter 的 scaling（讓字型與元件以正確倍率呈現，減少顆粒感）
    try:
        import tkinter as tk
        dpi = None
        try:
            user32 = ctypes.windll.user32
            if hasattr(user32, 'GetDpiForSystem'):
                dpi = user32.GetDpiForSystem()
        except Exception:
            dpi = None

        if dpi is None:
            try:
                hdc = ctypes.windll.user32.GetDC(0)
                LOGPIXELSX = 88
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, LOGPIXELSX)
                ctypes.windll.user32.ReleaseDC(0, hdc)
            except Exception:
                dpi = 96

        scaling = max(1.0, float(dpi) / 72.0)
        # 允許透過環境變數覆寫 scaling（方便做 A/B 測試）
        try:
            env = os.environ.get("NB_SCALING")
            if env:
                scaling = float(env)
        except Exception:
            pass
        root = tk.Tk()
        root.withdraw()
        try:
            root.tk.call('tk', 'scaling', scaling)
        finally:
            root.destroy()

        # 診斷輸出：在終端列印偵測到的 DPI 與套用的 scaling，方便排查顆粒感問題
        try:
            print(f"[DPI DIAG] detected_dpi={dpi!r}, applied_scaling={scaling!r} (NB_SCALING={os.environ.get('NB_SCALING')})")
        except Exception:
            pass
    except Exception:
        pass

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
