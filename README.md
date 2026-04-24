# NotebookLM 檔案切分工具

將超大檔案自動切分成符合 [NotebookLM](https://notebooklm.google.com/) 上傳限制的多個部分。

## NotebookLM 限制

| 類型 | 單檔上限 |
|------|----------|
| 音訊 / 影片 | 200 MB |
| 文字（txt、md） | 500,000 字 |

## 功能

- 拖放或選擇檔案（支援整個資料夾批次處理）
- 音影片切分使用 FFmpeg `-c copy`，**不重新編碼**，速度接近磁碟讀寫
- 文字切分自動在段落或句子邊界分割，不截斷詞句
- 多檔案並行處理，進度條即時顯示
- 輸出路徑：`output/{日期}/{原始檔名}/{原始檔名}, part1.xxx`

## 支援格式

| 類別 | 副檔名 |
|------|--------|
| 音訊 | mp3、wav、m4a、aac、flac、ogg、wma、opus |
| 影片 | mp4、mkv、mov、avi、webm |
| 文字 | txt、md |

## 安裝與執行

**需求：** Python 3.11+

```bash
# 1. 安裝 Python 套件
pip install -r requirements.txt

# 2. 下載 FFmpeg（音影片切分必要）
#    https://www.gyan.dev/ffmpeg/builds/ → ffmpeg-release-essentials.zip
#    解壓後將 ffmpeg.exe 與 ffprobe.exe 放入：
#    assets/ffmpeg/ffmpeg.exe
#    assets/ffmpeg/ffprobe.exe
#
#    若系統 PATH 已安裝 FFmpeg 可跳過此步驟

# 3. 啟動
python main.py
```

## 輸出範例

```
output/
└── 2026-04-24/
    ├── lecture/
    │   ├── lecture, part1.mp4   # ~200 MB
    │   ├── lecture, part2.mp4   # ~200 MB
    │   └── lecture, part3.mp4   # 剩餘部分
    └── notes/
        ├── notes, part1.txt     # ≤500,000 字
        └── notes, part2.txt     # 剩餘部分
```
