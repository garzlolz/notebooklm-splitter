import shutil
from pathlib import Path

from src.models.job import SplitJob, JobStatus
from src.splitter.base import BaseSplitter

MAX_CHARS = 500_000
SAFE_CHARS = 499_000

_PARAGRAPH = "\n\n"
_SENTENCE_ENDINGS = {"。", "！", "？", ".", "!", "?", "\n"}
_SEARCH_WINDOW = 2000


class TextSplitter(BaseSplitter):
    SUPPORTED_EXTENSIONS = {".txt", ".md"}

    def _find_split_point(self, text: str, end: int) -> int:
        # 優先：段落邊界（空白行），且至少填滿 50%
        idx = text.rfind(_PARAGRAPH, 0, end)
        if idx != -1 and idx > end * 0.5:
            return idx + len(_PARAGRAPH)

        # 次要：句子結尾，在最後 _SEARCH_WINDOW 字元內往回找
        for pos in range(end - 1, max(0, end - _SEARCH_WINDOW), -1):
            if text[pos] in _SENTENCE_ENDINGS:
                return pos + 1

        # Fallback：最後一個換行
        idx = text.rfind("\n", 0, end)
        if idx != -1 and idx > end * 0.3:
            return idx + 1

        return end

    def split(self, job: SplitJob) -> None:
        try:
            job.status = JobStatus.RUNNING
            src = job.source_path
            content = src.read_text(encoding="utf-8-sig", errors="replace")
            total_chars = len(content)

            job.output_dir.mkdir(parents=True, exist_ok=True)

            if total_chars <= MAX_CHARS:
                shutil.copy2(src, job.output_dir / src.name)
                job.parts_count = 1
                job.progress = 1.0
                job.status = JobStatus.DONE
                if job.on_progress:
                    job.on_progress(1.0)
                if job.on_done:
                    job.on_done(1)
                return

            parts: list[str] = []
            cursor = 0
            while cursor < total_chars:
                remaining = total_chars - cursor
                if remaining <= MAX_CHARS:
                    parts.append(content[cursor:])
                    break
                split_at = self._find_split_point(content, cursor + SAFE_CHARS)
                parts.append(content[cursor:split_at])
                cursor = split_at

            stem = src.stem
            suffix = src.suffix
            total_parts = len(parts)

            for i, part_text in enumerate(parts):
                out_name = f"{stem}, part{i + 1}{suffix}"
                (job.output_dir / out_name).write_text(part_text, encoding="utf-8")
                progress = (i + 1) / total_parts
                job.progress = progress
                if job.on_progress:
                    job.on_progress(progress)

            job.parts_count = total_parts
            job.status = JobStatus.DONE
            if job.on_done:
                job.on_done(total_parts)

        except Exception as exc:
            job.status = JobStatus.ERROR
            job.error_msg = str(exc)
            if job.on_error:
                job.on_error(str(exc))
