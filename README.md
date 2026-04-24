# NotebookLM 檔案切分工具

將超大檔案自動切分成符合 [NotebookLM](https://notebooklm.google.com/) 上傳限制的多個部分。採用**流暢的 GUI 設計**，支援拖放檔案，多檔案並行處理。

## 快速開始

### 推薦方式 — 從源碼執行

```bash
# 1. 克隆或下載本專案
git clone https://github.com/yourusername/notebooklm-splitter.git
cd notebooklm-splitter

# 2. 建立虛擬環境
python3.11 -m venv .venv
source .venv/bin/activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 啟動 GUI
python main.py
```

## NotebookLM 限制

| 類型 | 單檔上限 |
|------|----------|
| 音訊 / 影片 | 200 MB |
| 文字（txt、md） | 500,000 字 |

## 功能特色

- **直觀的拖放介面** — 拖放檔案或資料夾到視窗，自動批次處理
- **零損失音影片切分** — 使用 FFmpeg `-c copy`，不重新編碼，速度接近磁碟讀寫
- **智能文字切分** — 優先在段落（`\n\n`）和句子邊界分割，不截斷詞句
- **多檔案並行** — 同時處理多個檔案，實時進度顯示
- **自動輸出組織** — `output/{日期}/{檔名}/` 結構，便於管理

## 支援格式

| 類別 | 副檔名 |
|------|--------|
| 🎵 音訊 | mp3、wav、m4a、aac、flac、ogg、wma、opus |
| 🎬 影片 | mp4、mkv、mov、avi、webm |
| 📄 文字 | txt、md |

## 安裝與配置

### 系統需求

- **Python 3.11+**（[下載](https://www.python.org/downloads/)）
- **FFmpeg**（[下載](https://www.gyan.dev/ffmpeg/builds/)）— 用於音影片切分

#### macOS 特定需求

推薦使用 [Homebrew](https://brew.sh/) 安裝 Python 和 FFmpeg：

```bash
# 安裝 Homebrew（若未安裝）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝 Python 3.11
brew install python@3.11

# 安裝 FFmpeg
brew install ffmpeg

# 驗證
python3.11 --version
ffmpeg -version
```

### FFmpeg 配置

**選項 A：系統已安裝 FFmpeg**

如果系統 `PATH` 環境變數已包含 FFmpeg，可跳過後續步驟。驗證方法：
```bash
ffmpeg -version
ffprobe -version
```

**選項 B：下載 FFmpeg 到本專案（推薦開發環境）**

1. 下載：[ffmpeg-release-essentials.zip](https://www.gyan.dev/ffmpeg/builds/)
2. 解壓縮
3. 取出以下兩個檔案：
   - `ffmpeg.exe` 或 `ffmpeg`
   - `ffprobe.exe` 或 `ffprobe`
4. 放入本專案的 `assets/ffmpeg/` 資料夾

目錄結構應為：
```
notebooklm-splitter/
├── assets/
│   └── ffmpeg/
│       ├── ffmpeg         (或 ffmpeg.exe)
│       └── ffprobe        (或 ffprobe.exe)
├── main.py
└── ...
```

## 編譯成執行檔（可選）

若想自行打包成獨立執行檔（開發用途），執行以下命令會自動偵測你的作業系統並產生對應的應用程式：

```bash
bash build.sh
```

### 各平台的打包結果

| 平台 | 輸出格式 | 執行方式 |
|------|--------|--------|
| **macOS** | `dist/NotebookLM切分工具.app` | 雙擊 `.app` 檔案，或執行 `open dist/NotebookLM切分工具.app` |
| **Linux** | `dist/NotebookLM切分工具` | 執行 `./dist/NotebookLM切分工具` |
| **Windows** | `dist/NotebookLM切分工具.exe` | 雙擊 `.exe` 檔案 |

> **注意：** 
> - 首次打包需自動安裝 PyInstaller，請確保網路連線正常
> - 打包檔案僅用於開發測試，不上傳至倉庫（見 `.gitignore`）
> - macOS 可能需要在「系統偏好設定 > 安全性」允許執行應用程式

## 輸出範例

```
output/
└── 2026-04-24/
    ├── 演講錄音/
    │   ├── 演講錄音, part1.mp4    # ~200 MB
    │   ├── 演講錄音, part2.mp4    # ~200 MB
    │   └── 演講錄音, part3.mp4    # 剩餘部分
    └── 會議筆記/
        ├── 會議筆記, part1.txt    # ≤500,000 字
        └── 會議筆記, part2.txt    # 剩餘部分
```

每個部分已自動最佳化，可直接上傳至 NotebookLM。

## 架構概覽

```
src/
├── app.py              # GUI 主視窗（CustomTkinter）
├── models/
│   └── job.py          # SplitJob 資料類別
├── splitter/
│   ├── base.py         # 抽象基類
│   ├── media_splitter.py   # 音影片切分（FFmpeg）
│   └── text_splitter.py    # 文字切分（Unicode 計數）
└── utils/
    ├── file_utils.py   # 檔案操作輔助函式
    └── ffmpeg_utils.py  # FFmpeg 路徑檢測（支援 PyInstaller）
```

## 常見問題

### Q: 為什麼音影片切分比較慢？
A: 使用 FFmpeg `-c copy` 不重新編碼，速度已接近磁碟讀寫限制。如果仍覺得慢，可檢查：
- 磁碟是否為機械硬碟（HDD）或網路磁碟
- 系統是否有其他高 I/O 程序在執行

### Q: 文字切分後部分內容丟失？
A: 不會。本工具計數方式與 NotebookLM 一致（Unicode 字碼點），並優先在語意邊界（段落/句子）切分。

### Q: 可以自訂輸出路徑嗎？
A: 目前輸出固定為 `output/{日期}/{檔名}/`。如有需要，可修改 `src/utils/file_utils.py` 的 `get_output_dir()` 函式。

### Q: FFmpeg 找不到？
A: 確認以下其中之一：
1. 系統 PATH 已安裝 FFmpeg（執行 `ffmpeg -version` 驗證）
2. 已將 `ffmpeg.exe` 與 `ffprobe.exe` 放入 `assets/ffmpeg/`

## 授權

MIT License

## 相關資源

- [NotebookLM 官網](https://notebooklm.google.com/)
- [FFmpeg 官網](https://ffmpeg.org/)
- [CustomTkinter 文件](https://github.com/TomSchimansky/CustomTkinter)

