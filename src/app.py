from __future__ import annotations

import os
import platform
import subprocess
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton, QProgressBar, QCheckBox, QScrollArea, 
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from src.models.job import SplitJob, JobStatus
from src.splitter import get_splitter
from src.utils.file_utils import (
    get_output_dir, is_supported, is_media_file, is_video_file, human_size
)

# ── QSS 樣式表 ──────────────────────────────────────────────
STYLE_SHEET = """
QMainWindow {
    background-color: #121214;
}

QWidget {
    font-family: "Microsoft JhengHei UI", "Segoe UI", sans-serif;
    color: #e4e4e7;
    font-size: 13px;
}

QLabel#HeaderTitle {
    font-size: 20px;
    font-weight: bold;
    color: #ffffff;
}

QFrame#DropZone {
    background-color: #18181b;
    border: 2px dashed #3f3f46;
    border-radius: 12px;
}

QFrame#DropZone[dragOver="true"] {
    border: 2px dashed #3b82f6;
    background-color: #1e293b;
}

QLabel#DropZoneIcon {
    font-size: 40px;
}

QLabel#DropZoneTitle {
    font-size: 14px;
    font-weight: bold;
    color: #f4f4f5;
}

QLabel#DropZoneSub {
    font-size: 12px;
    color: #71717a;
}

QLabel#SectionTitle {
    font-size: 13px;
    font-weight: bold;
    color: #a1a1aa;
}

QScrollArea {
    border: 1px solid #27272a;
    border-radius: 10px;
    background-color: #18181b;
}

QScrollArea > QWidget > QWidget {
    background-color: #18181b;
}

QFrame#FileRow {
    background-color: #1f1f23;
    border: 1px solid #2d2d30;
    border-radius: 8px;
}

QLabel#FileName {
    font-size: 13px;
    font-weight: bold;
    color: #f4f4f5;
}

QLabel#FileSize {
    font-size: 11px;
    color: #a1a1aa;
}

QCheckBox {
    font-size: 11px;
    color: #a1a1aa;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #3f3f46;
    border-radius: 3px;
    background-color: #18181b;
}

QCheckBox::indicator:checked {
    border: 1px solid #3b82f6;
    background-color: #3b82f6;
}

QProgressBar {
    background-color: #27272a;
    border: none;
    border-radius: 3px;
    height: 6px;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 3px;
}

QProgressBar#DoneProgress::chunk {
    background-color: #10b981;
}

QProgressBar#ErrorProgress::chunk {
    background-color: #ef4444;
}

QLabel#StatusLabel {
    font-size: 11px;
    color: #a1a1aa;
}

QLabel#StatusLabel[status="running"] {
    color: #06b6d4;
}

QLabel#StatusLabel[status="done"] {
    color: #10b981;
}

QLabel#StatusLabel[status="error"] {
    color: #ef4444;
}

QPushButton {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 6px 12px;
    color: #e4e4e7;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #323235;
    border-color: #52525b;
}

QPushButton:pressed {
    background-color: #1c1c1e;
}

QPushButton#StartBtn {
    background-color: #2563eb;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#StartBtn:hover {
    background-color: #3b82f6;
    border-color: #60a5fa;
}

QPushButton#StartBtn:pressed {
    background-color: #1d4ed8;
}

QScrollBar:vertical {
    border: none;
    background: #18181b;
    width: 8px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:vertical {
    background: #27272a;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #3f3f46;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

# ── 執行緒安全訊號橋接器 ──────────────────────────────────────
class JobSignals(QObject):
    progress = Signal(float)
    status = Signal(str)
    done = Signal(int)
    error = Signal(str)


# ── 檔案清單列元件 ───────────────────────────────────────────
class FileRow(QFrame):
    def __init__(self, job: SplitJob, parent=None):
        super().__init__(parent)
        self.setObjectName("FileRow")
        self.job = job
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # 第一列：檔名、檔案大小、轉換 m4a 選框
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        
        self.name_lbl = QLabel(job.source_path.name)
        self.name_lbl.setObjectName("FileName")
        row1.addWidget(self.name_lbl, stretch=1)
        
        size_bytes = job.source_path.stat().st_size if job.source_path.exists() else 0
        self.size_lbl = QLabel(human_size(size_bytes))
        self.size_lbl.setObjectName("FileSize")
        row1.addWidget(self.size_lbl)
        
        if is_video_file(job.source_path):
            self.m4a_cb = QCheckBox("轉換為 m4a")
            self.m4a_cb.setChecked(job.convert_to_m4a)
            self.m4a_cb.stateChanged.connect(self._toggle_m4a)
            row1.addWidget(self.m4a_cb)
        else:
            self.m4a_cb = None
            
        layout.addLayout(row1)
        
        # 第二列：進度條、狀態標籤
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        row2.addWidget(self.progress, stretch=1)
        
        self.status_lbl = QLabel("等待中")
        self.status_lbl.setObjectName("StatusLabel")
        self.status_lbl.setMinimumWidth(85)
        self.status_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row2.addWidget(self.status_lbl)
        
        layout.addLayout(row2)
        
    def _toggle_m4a(self, state: int) -> None:
        self.job.convert_to_m4a = self.m4a_cb.isChecked()

    # ── UI 更新方法 ──
    def update_status(self, text: str) -> None:
        self.status_lbl.setText(text)
        self.status_lbl.setProperty("status", "running")
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)

    def update_progress(self, value: float) -> None:
        val_percent = int(value * 100)
        self.progress.setValue(val_percent)
        self.status_lbl.setText(f"{val_percent}%")
        self.status_lbl.setProperty("status", "running")
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)

    def mark_done(self, parts: int) -> None:
        self.progress.setValue(100)
        self.progress.setObjectName("DoneProgress")
        self.progress.style().unpolish(self.progress)
        self.progress.style().polish(self.progress)
        
        self.status_lbl.setText(f"完成（{parts} 個）")
        self.status_lbl.setProperty("status", "done")
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)

    def mark_error(self, msg: str) -> None:
        self.progress.setValue(100)
        self.progress.setObjectName("ErrorProgress")
        self.progress.style().unpolish(self.progress)
        self.progress.style().polish(self.progress)
        
        self.status_lbl.setText("錯誤")
        self.status_lbl.setProperty("status", "error")
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)


# ── 拖放檔案區元件 ───────────────────────────────────────────
class DropZone(QFrame):
    def __init__(self, on_files, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.on_files = on_files
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 24, 20, 24)
        
        self.icon_lbl = QLabel("📁")
        self.icon_lbl.setObjectName("DropZoneIcon")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_lbl)
        
        self.title_lbl = QLabel("拖放檔案 / 資料夾到此處")
        self.title_lbl.setObjectName("DropZoneTitle")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_lbl)
        
        self.sub_lbl = QLabel("或點擊選擇檔案")
        self.sub_lbl.setObjectName("DropZoneSub")
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sub_lbl)
        
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
            
    def dragLeaveEvent(self, event) -> None:
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        
    def dropEvent(self, event: QDropEvent) -> None:
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        
        paths = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path:
                paths.append(Path(local_path))
        if paths:
            self.on_files(paths)
            
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.select_files()
            
    def select_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "選擇要切分的檔案",
            "",
            "支援的格式 (*.mp3 *.mp4 *.wav *.m4a *.aac *.flac *.ogg *.mkv *.mov *.avi *.webm *.wma *.opus *.txt *.md);;"
            "音訊/影片 (*.mp3 *.mp4 *.wav *.m4a *.aac *.flac *.ogg *.mkv *.mov *.avi *.webm *.wma *.opus);;"
            "文字檔 (*.txt *.md);;"
            "所有檔案 (*.*)"
        )
        if paths:
            self.on_files([Path(p) for p in paths])


# ── 主視窗 ──────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NotebookLM 檔案切分工具")
        self.resize(750, 620)
        self.setMinimumSize(650, 500)
        
        self._jobs: list[SplitJob] = []
        self._rows: dict[int, FileRow] = {}  # id(job) -> FileRow
        self._lock = threading.Lock()
        
        # 套用樣式表
        self.setStyleSheet(STYLE_SHEET)
        
        # 主面板與版面配置
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # 頂部標題
        self.title_lbl = QLabel("NotebookLM 檔案切分工具")
        self.title_lbl.setObjectName("HeaderTitle")
        main_layout.addWidget(self.title_lbl)
        
        # 拖放檔案區
        self.drop_zone = DropZone(on_files=self._add_files)
        self.drop_zone.setFixedHeight(140)
        main_layout.addWidget(self.drop_zone)
        
        # 區段標題
        self.list_title = QLabel("待切分清單")
        self.list_title.setObjectName("SectionTitle")
        main_layout.addWidget(self.list_title)
        
        # 滾動區域 (清單)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("ListScroll")
        
        self.scroll_widget = QWidget()
        self.list_layout = QVBoxLayout(self.scroll_widget)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll)
        
        # 底部控制欄
        bottom_frame = QWidget()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)
        
        self.clear_btn = QPushButton("清除完成項目")
        self.clear_btn.setObjectName("ClearBtn")
        self.clear_btn.clicked.connect(self._clear_done)
        bottom_layout.addWidget(self.clear_btn)
        
        self.out_lbl = QLabel("📁 輸出：output/{日期}/{檔名}/")
        self.out_lbl.setObjectName("OutPathLabel")
        self.out_lbl.setStyleSheet("color: #71717a; font-size: 11px;")
        bottom_layout.addWidget(self.out_lbl, stretch=1)
        
        self.open_btn = QPushButton("開啟資料夾")
        self.open_btn.setObjectName("OpenFolderBtn")
        self.open_btn.clicked.connect(self._open_output)
        bottom_layout.addWidget(self.open_btn)
        
        self.start_btn = QPushButton("▶ 開始切分")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.clicked.connect(self._start_all)
        bottom_layout.addWidget(self.start_btn)
        
        main_layout.addWidget(bottom_frame)
        
        # 建立初始狀態 (顯示空清單提示)
        self.empty_lbl = None
        self._refresh_list()

    # ── 檔案管理 ─────────────────────────────────────────────
    def _add_files(self, paths: list[Path]) -> None:
        added = 0
        unsupported: list[str] = []
        for path in paths:
            if path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file():
                        r = self._try_add(child)
                        if r == "ok":
                            added += 1
                        elif r == "unsupported":
                            unsupported.append(child.name)
            else:
                r = self._try_add(path)
                if r == "ok":
                    added += 1
                elif r == "unsupported":
                    unsupported.append(path.name)
                    
        if added:
            self._refresh_list()
        if unsupported:
            QMessageBox.warning(
                self,
                "不支援的檔案",
                "以下檔案格式不支援，已略過：\n" + "\n".join(unsupported[:10])
            )
            
    def _try_add(self, path: Path) -> str:
        if not is_supported(path):
            return "unsupported"
        with self._lock:
            for j in self._jobs:
                if j.source_path == path:
                    if j.status in (JobStatus.DONE, JobStatus.ERROR):
                        j.status = JobStatus.PENDING
                        j.progress = 0.0
                        j.parts_count = 0
                        j.error_msg = None
                        return "ok"
                    return "duplicate"
            out_dir = get_output_dir(path)
            job = SplitJob(source_path=path, output_dir=out_dir)
            self._jobs.append(job)
        return "ok"

    def _refresh_list(self) -> None:
        with self._lock:
            # 1. 移除不存在於 _jobs 的 row widgets
            current_job_ids = {id(j) for j in self._jobs}
            removed_ids = []
            for job_id, row in list(self._rows.items()):
                if job_id not in current_job_ids:
                    self.list_layout.removeWidget(row)
                    row.deleteLater()
                    removed_ids.append(job_id)
            for job_id in removed_ids:
                del self._rows[job_id]
                
            # 2. 如果目前有任務且顯示空清單提示，則清除提示
            if self.empty_lbl is not None:
                if self._jobs:
                    self.list_layout.removeWidget(self.empty_lbl)
                    self.empty_lbl.deleteLater()
                    self.empty_lbl = None
            
            # 3. 補齊新增任務的 row widgets
            for job in self._jobs:
                job_id = id(job)
                if job_id not in self._rows:
                    row = FileRow(job)
                    self.list_layout.addWidget(row)
                    self._rows[job_id] = row
                    
                    # 恢復進度與狀態顯示
                    if job.status == JobStatus.DONE:
                        row.mark_done(job.parts_count)
                    elif job.status == JobStatus.ERROR:
                        row.mark_error(job.error_msg or "")
                    elif job.status == JobStatus.RUNNING:
                        row.update_progress(job.progress)
            
            # 4. 如果完全沒有任務且未顯示空清單提示，則顯示
            if not self._jobs and self.empty_lbl is None:
                self.empty_lbl = QLabel("尚未加入任何檔案")
                self.empty_lbl.setObjectName("EmptyLabel")
                self.empty_lbl.setStyleSheet("color: #71717a; font-size: 13px; padding: 40px;")
                self.empty_lbl.setAlignment(Qt.AlignCenter)
                self.list_layout.addWidget(self.empty_lbl)

    def _clear_done(self) -> None:
        with self._lock:
            self._jobs = [j for j in self._jobs if j.status != JobStatus.DONE]
        self._refresh_list()

    # ── 切分邏輯與執行 ──────────────────────────────────────────
    def _start_all(self) -> None:
        pending = [j for j in self._jobs if j.status == JobStatus.PENDING]
        if not pending:
            QMessageBox.information(self, "提示", "沒有等待切分的檔案。")
            return
            
        for job in pending:
            row = self._rows.get(id(job))
            if row is None:
                continue
                
            # 建立 Job-specific 訊號橋接器
            signals = JobSignals()
            signals.progress.connect(row.update_progress)
            signals.status.connect(row.update_status)
            signals.done.connect(row.mark_done)
            signals.error.connect(row.mark_error)
            
            # 將工作進度回呼綁定到訊號發送
            job.on_progress = lambda val, sig=signals: sig.progress.emit(val)
            job.on_status = lambda text, sig=signals: sig.status.emit(text)
            job.on_done = lambda parts, sig=signals: sig.done.emit(parts)
            job.on_error = lambda msg, sig=signals: sig.error.emit(msg)
            
            # 保持 Reference 避免信號被回收
            job._signals = signals
            
            # 啟動背景工作執行緒
            t = threading.Thread(target=self._run_job, args=(job,), daemon=True)
            t.start()

    def _run_job(self, job: SplitJob) -> None:
        ext = job.source_path.suffix
        try:
            splitter = get_splitter(ext)
            splitter.split(job)
        except ValueError as exc:
            job.status = JobStatus.ERROR
            job.error_msg = str(exc)
            if job.on_error:
                job.on_error(str(exc))

    # ── 輸出資料夾 ───────────────────────────────────────────
    def _open_output(self) -> None:
        out = Path("output")
        if not out.exists():
            QMessageBox.information(self, "提示", "output 資料夾尚未建立，請先執行切分。")
            return
        
        # 根據系統開啟資料夾
        if platform.system() == "Windows":
            os.startfile(str(out.resolve()))
        elif platform.system() == "Darwin": # macOS
            subprocess.run(["open", str(out.resolve())])
        else: # Linux
            subprocess.run(["xdg-open", str(out.resolve())])
