# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 執行方式

```bash
# 安裝依賴（一次）
pip install -r requirements.txt

# 啟動 GUI
python main.py
```

FFmpeg 需手動下載並放入 `assets/ffmpeg/`：
- 下載來源：https://www.gyan.dev/ffmpeg/builds/ → ffmpeg-release-essentials.zip
- 解壓後取 `ffmpeg.exe` 與 `ffprobe.exe` 放入 `assets/ffmpeg/`
- 若系統 PATH 已有 FFmpeg，可跳過此步驟

## 架構概覽

```
main.py          進入點，設定 sys.path 後啟動 App
src/
  app.py         GUI 主視窗（CustomTkinter + tkinterdnd2）
  models/job.py  SplitJob dataclass：持有路徑、狀態、進度、回呼函數
  splitter/
    __init__.py  get_splitter(ext) factory
    base.py      BaseSplitter ABC
    text_splitter.py   文字切分（≤500,000字/檔）
    media_splitter.py  音影片切分（≤200MB/檔，FFmpeg -c copy）
  utils/
    file_utils.py    get_output_dir(), is_media_file(), human_size()
    ffmpeg_utils.py  get_ffmpeg_path() / get_ffprobe_path()（支援 PyInstaller 打包）
```

## 切分邏輯重點

**音影片（MediaSplitter）：**
- 用 ffprobe 取得 duration 與 bitrate
- `max_seconds = (200MB × 8 / bitrate) × 0.95`（留 5% 緩衝）
- FFmpeg 指令：`-ss {start} -i input -t {max_seconds} -c copy -avoid_negative_ts make_zero`
- `-ss` 放在 `-i` 前（input seeking，速度快）；`-c copy` 不重新編碼

**文字（TextSplitter）：**
- Python `len(str)` = Unicode code point 數，對應 NotebookLM 字符限制
- 每段目標 499,000 字（留緩衝）
- 切分點優先順序：段落邊界（`\n\n`）→ 句子結尾 → 換行 → 硬切
- `utf-8-sig` 讀取自動去 BOM

**輸出路徑：** `output/{YYYY-MM-DD}/{原始檔名}/{原始檔名}, part1{副檔名}`

## GUI 架構

- `App` 根據 tkinterdnd2 是否可用，選擇繼承 `dnd.Tk` 或 `ctk.CTk`
- 每個切分任務在獨立 daemon Thread 執行
- UI 更新透過 `widget.after(0, callback)` 切回主執行緒
- `SplitJob.on_progress` / `on_done` / `on_error` 是 GUI 注入的回呼函數

## 支援格式

| 類型 | 副檔名 |
|------|--------|
| 音訊 | mp3 wav m4a aac flac ogg wma opus |
| 影片 | mp4 mkv mov avi webm |
| 文字 | txt md |
