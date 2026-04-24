from src.splitter.media_splitter import MediaSplitter
from src.splitter.text_splitter import TextSplitter
from src.splitter.base import BaseSplitter

_SPLITTERS: list[type[BaseSplitter]] = [MediaSplitter, TextSplitter]


def get_splitter(ext: str) -> BaseSplitter:
    for cls in _SPLITTERS:
        if cls.can_handle(ext):
            return cls()
    raise ValueError(f"不支援的副檔名：{ext}")
