#!/bin/bash
set -e

echo "========================================"
echo "  NotebookLM 切分工具 - 打包程式"
echo "========================================"
echo

echo "[1/3] 安裝 / 更新 PyInstaller..."
pip install --quiet --upgrade pyinstaller

echo "[2/3] 清除舊的打包結果..."
rm -rf dist build "NotebookLM切分工具.spec" 2>/dev/null || true

echo "[3/3] 開始打包..."
pyinstaller --onefile --windowed \
  --name "NotebookLM切分工具" \
  --add-data "assets:assets" \
  --collect-data tkinterdnd2 \
  --collect-data customtkinter \
  main.py

if [ $? -eq 0 ]; then
  echo
  echo "========================================"
  echo "  打包完成！"
  echo "  執行檔位置：dist/NotebookLM切分工具.exe"
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
