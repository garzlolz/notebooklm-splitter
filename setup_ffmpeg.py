"""
自動下載 FFmpeg 並放到 assets/ffmpeg/
執行方式：python setup_ffmpeg.py
"""
import io
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
DEST = Path(__file__).parent / "assets" / "ffmpeg"
BINARIES = {"ffmpeg.exe", "ffprobe.exe"}


def already_exists() -> bool:
    return all((DEST / b).exists() for b in BINARIES)


def download_with_progress(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        buf = io.BytesIO()
        downloaded = 0
        chunk = 65536
        while True:
            data = resp.read(chunk)
            if not data:
                break
            buf.write(data)
            downloaded += len(data)
            if total:
                pct = downloaded / total * 100
                bar = "#" * int(pct // 2)
                print(f"\r  [{bar:<50}] {pct:5.1f}%  {downloaded/1e6:.1f}/{total/1e6:.1f} MB",
                      end="", flush=True)
        print()
        return buf.getvalue()


def extract_binaries(data: bytes) -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.namelist():
            filename = Path(member).name
            if filename in BINARIES:
                print(f"  解壓縮 {filename} ...")
                (DEST / filename).write_bytes(zf.read(member))


def main() -> None:
    if already_exists():
        print("FFmpeg 已存在於 assets/ffmpeg/，無需重新下載。")
        return

    print(f"下載 FFmpeg from:\n  {FFMPEG_URL}\n")
    try:
        data = download_with_progress(FFMPEG_URL)
    except URLError as e:
        print(f"下載失敗：{e}", file=sys.stderr)
        sys.exit(1)

    print("解壓縮中 ...")
    extract_binaries(data)

    if already_exists():
        print(f"\n完成！FFmpeg 已安裝至 {DEST}")
    else:
        missing = [b for b in BINARIES if not (DEST / b).exists()]
        print(f"警告：未找到以下檔案：{missing}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
