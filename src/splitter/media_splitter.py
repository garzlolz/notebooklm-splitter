import json
import shutil
import subprocess
from pathlib import Path

from src.models.job import SplitJob, JobStatus
from src.splitter.base import BaseSplitter
from src.utils.ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path
from src.utils.file_utils import VIDEO_EXTENSIONS

MAX_BYTES = 200 * 1024 * 1024  # 200 MB
SAFETY_FACTOR = 0.95
MAX_SPLIT_ATTEMPTS = 6  # 單一片段超出大小上限時，最多重切幾次
MIN_SEGMENT_SECONDS = 2.0  # 重切時秒數下限，避免無窮縮小
RESHRINK_SAFETY = 0.97  # 依實際檔案大小重新估算秒數時的額外緩衝


class MediaSplitter(BaseSplitter):
    SUPPORTED_EXTENSIONS = {
        ".mp3", ".mp4", ".wav", ".m4a", ".aac",
        ".flac", ".ogg", ".mkv", ".mov", ".avi",
        ".webm", ".wma", ".opus",
    }

    def _probe(self, path: Path) -> dict:
        cmd = [
            get_ffprobe_path(),
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
        return json.loads(result.stdout)["format"]

    def _convert_to_m4a(self, src: Path, dest: Path) -> None:
        cmd = [
            get_ffmpeg_path(), "-y",
            "-i", str(src),
            "-vn", "-c:a", "aac", "-b:a", "128k",
            str(dest),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _cut_segment(self, ffmpeg: str, src: Path, start: float, duration: float, out_path: Path) -> None:
        cmd = [
            ffmpeg, "-y",
            "-ss", str(start),
            "-i", str(src),
            "-t", str(duration),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-map", "0",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def split(self, job: SplitJob) -> None:
        try:
            job.status = JobStatus.RUNNING
            src = job.source_path
            job.output_dir.mkdir(parents=True, exist_ok=True)

            temp_m4a: Path | None = None
            output_suffix = src.suffix

            if job.convert_to_m4a and src.suffix.lower() in VIDEO_EXTENSIONS:
                if job.on_status:
                    job.on_status("轉換中…")
                temp_m4a = job.output_dir / f"__converting__{src.stem}.m4a"
                self._convert_to_m4a(src, temp_m4a)
                src = temp_m4a
                output_suffix = ".m4a"
                if job.on_status:
                    job.on_status("切分中…")

            try:
                file_size = src.stat().st_size
                stem = job.source_path.stem

                if file_size <= MAX_BYTES:
                    out_path = job.output_dir / f"{stem}{output_suffix}"
                    shutil.copy2(src, out_path)
                    job.parts_count = 1
                    job.progress = 1.0
                    job.status = JobStatus.DONE
                    if job.on_progress:
                        job.on_progress(1.0)
                    if job.on_done:
                        job.on_done(1)
                    return

                fmt = self._probe(src)
                total_duration = float(fmt["duration"])
                bitrate = int(fmt.get("bit_rate", 0))

                if bitrate > 0:
                    max_seconds = (MAX_BYTES * 8 / bitrate) * SAFETY_FACTOR
                else:
                    max_seconds = (total_duration * MAX_BYTES / file_size) * SAFETY_FACTOR

                ffmpeg = get_ffmpeg_path()
                parts_count = 0
                start = 0.0

                while start < total_duration - 1e-3:
                    duration = min(max_seconds, total_duration - start)
                    parts_count += 1
                    out_name = f"{stem}, part{parts_count}{output_suffix}"
                    out_path = job.output_dir / out_name

                    for attempt in range(MAX_SPLIT_ATTEMPTS):
                        self._cut_segment(ffmpeg, src, start, duration, out_path)
                        out_size = out_path.stat().st_size
                        if out_size <= MAX_BYTES or duration <= MIN_SEGMENT_SECONDS:
                            break
                        # 該片段實際位元率高於全片平均值（VBR），依實際大小重新估算秒數後重切
                        duration = max(
                            duration * (MAX_BYTES / out_size) * RESHRINK_SAFETY,
                            MIN_SEGMENT_SECONDS,
                        )

                    start += duration
                    progress = min(start / total_duration, 1.0)
                    job.progress = progress
                    if job.on_progress:
                        job.on_progress(progress)

                job.parts_count = parts_count
                job.status = JobStatus.DONE
                if job.on_done:
                    job.on_done(parts_count)

            finally:
                if temp_m4a and temp_m4a.exists():
                    temp_m4a.unlink()

        except Exception as exc:
            job.status = JobStatus.ERROR
            job.error_msg = str(exc)
            if job.on_error:
                job.on_error(str(exc))
