from datetime import date
from pathlib import Path

MEDIA_EXTENSIONS = {
    ".mp3", ".mp4", ".wav", ".m4a", ".aac",
    ".flac", ".ogg", ".mkv", ".mov", ".avi",
    ".webm", ".wma", ".opus",
}

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}

TEXT_EXTENSIONS = {".txt", ".md"}


def get_output_dir(source_path: Path, base_output: Path = Path("output")) -> Path:
    today = date.today().strftime("%Y-%m-%d")
    return base_output / today / source_path.stem


def is_media_file(path: Path) -> bool:
    return path.suffix.lower() in MEDIA_EXTENSIONS


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def is_supported(path: Path) -> bool:
    return is_media_file(path) or is_text_file(path)


def human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    return f"{size_bytes / 1024 ** 3:.2f} GB"
