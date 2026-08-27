#!/bin/bash
set -e

echo "========================================"
echo "  NotebookLM 切分工具 - 打包程式"
echo "========================================"
echo

# 檢測作業系統
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
else
    OS="Unknown"
fi

echo "[1/3] 安裝 / 更新依賴與 PyInstaller..."
python -m pip install --quiet -r requirements.txt
python -m pip install --quiet --upgrade pyinstaller

echo "[2/3] 清除舊的打包結果..."
rm -rf dist build "NotebookLM切分工具.spec" 2>/dev/null || true

# 自動下載 FFmpeg 二進位（若尚未存在）
mkdir -p assets/ffmpeg
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ ! -f "assets/ffmpeg/ffmpeg" ]]; then
        FFMPEG_BIN=$(command -v ffmpeg || true)
        FFPROBE_BIN=$(command -v ffprobe || true)
        if [[ -n "$FFMPEG_BIN" && -n "$FFPROBE_BIN" ]]; then
            echo "複製系統 FFmpeg 至 assets/ffmpeg/..."
            cp "$FFMPEG_BIN" assets/ffmpeg/ffmpeg
            cp "$FFPROBE_BIN" assets/ffmpeg/ffprobe
        else
            echo "下載 FFmpeg (macOS)..."
            brew install ffmpeg 2>/dev/null || {
                echo "警告：無法自動安裝 FFmpeg，請手動安裝後再試。"
            }
            FFMPEG_BIN=$(command -v ffmpeg || true)
            FFPROBE_BIN=$(command -v ffprobe || true)
            [[ -n "$FFMPEG_BIN" ]] && cp "$FFMPEG_BIN" assets/ffmpeg/ffmpeg
            [[ -n "$FFPROBE_BIN" ]] && cp "$FFPROBE_BIN" assets/ffmpeg/ffprobe
        fi
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! command -v ffmpeg &>/dev/null && [[ ! -f "assets/ffmpeg/ffmpeg" ]]; then
        echo "下載 FFmpeg (Linux)..."
        sudo apt-get install -y ffmpeg 2>/dev/null || \
        sudo dnf install -y ffmpeg 2>/dev/null || {
            echo "警告：無法自動安裝 FFmpeg，請手動安裝後再試。"
        }
    fi
else
    # Windows (Git Bash / MSYS2)
    if [[ ! -f "assets/ffmpeg/ffmpeg.exe" ]]; then
        echo "下載 FFmpeg (Windows)..."
        FFMPEG_URL="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        curl -L --progress-bar "$FFMPEG_URL" -o _ffmpeg_tmp.zip
        unzip -q _ffmpeg_tmp.zip "*/bin/ffmpeg.exe" "*/bin/ffprobe.exe" -d _ffmpeg_extract
        find _ffmpeg_extract -name "ffmpeg.exe" -exec cp {} assets/ffmpeg/ \;
        find _ffmpeg_extract -name "ffprobe.exe" -exec cp {} assets/ffmpeg/ \;
        rm -rf _ffmpeg_tmp.zip _ffmpeg_extract
        echo "FFmpeg 已下載至 assets/ffmpeg/"
    fi
fi

echo "[3/3] 開始打包..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS: 打包成 .app 應用程式包
    echo "偵測到 macOS，打包成 .app..."
    python -m PyInstaller --windowed --onedir \
      --name "NotebookLM切分工具" \
      --add-data "assets:assets" \
      main.py
    OUTPUT_PATH="dist/NotebookLM切分工具.app"
else
    # Linux / Windows: 打包成獨立執行檔
    echo "打包成獨立執行檔..."
    python -m PyInstaller --onefile --windowed \
      --name "NotebookLM切分工具" \
      --add-data "assets:assets" \
      main.py
    OUTPUT_PATH="dist/NotebookLM切分工具"
fi

if [ $? -eq 0 ]; then
  echo
  echo "========================================"
  echo "  打包完成！（$OS）"
  echo "  執行檔位置：$OUTPUT_PATH"
  echo "========================================"
  
  # 跨平台打開 dist 文件夾
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    explorer dist
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    open dist
  else
    xdg-open dist 2>/dev/null || true
  fi
else
  echo
  echo "錯誤：打包失敗，請查看上方錯誤訊息"
  exit 1
fi
