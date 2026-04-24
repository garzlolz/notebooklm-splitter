import sys
from pathlib import Path


def _bundled(name: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent.parent
    return base / "assets" / "ffmpeg" / name


def get_ffmpeg_path() -> str:
    p = _bundled("ffmpeg.exe")
    return str(p) if p.exists() else "ffmpeg"


def get_ffprobe_path() -> str:
    p = _bundled("ffprobe.exe")
    return str(p) if p.exists() else "ffprobe"
