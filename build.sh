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

echo "[1/3] 安裝 / 更新 PyInstaller..."
pip install --quiet --upgrade pyinstaller

echo "[2/3] 清除舊的打包結果..."
rm -rf dist build "NotebookLM切分工具.spec" 2>/dev/null || true

echo "[3/3] 開始打包..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS: 打包成 .app 應用程式包
    echo "偵測到 macOS，打包成 .app..."
    pyinstaller --windowed --onedir \
      --name "NotebookLM切分工具" \
      --icon "assets/icon.icns" 2>/dev/null || \
    pyinstaller --windowed --onedir \
      --name "NotebookLM切分工具" \
      --add-data "assets:assets" \
      --collect-data tkinterdnd2 \
      --collect-data customtkinter \
      main.py
    OUTPUT_PATH="dist/NotebookLM切分工具.app"
else
    # Linux / Windows: 打包成獨立執行檔
    echo "打包成獨立執行檔..."
    pyinstaller --onefile --windowed \
      --name "NotebookLM切分工具" \
      --add-data "assets:assets" \
      --collect-data tkinterdnd2 \
      --collect-data customtkinter \
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
