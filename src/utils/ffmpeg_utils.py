import sys
import platform
from pathlib import Path


def _bundled(name: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent.parent
    return base / "assets" / "ffmpeg" / name


def _exe(base_name: str) -> str:
    """Return platform-appropriate binary name."""
    if platform.system() == "Windows":
        return base_name + ".exe"
    return base_name


def get_ffmpeg_path() -> str:
    p = _bundled(_exe("ffmpeg"))
    return str(p) if p.exists() else "ffmpeg"


def get_ffprobe_path() -> str:
    p = _bundled(_exe("ffprobe"))
    return str(p) if p.exists() else "ffprobe"
