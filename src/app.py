from __future__ import annotations

import os
import platform
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
try:
    import tkinterdnd2 as dnd
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from src.models.job import SplitJob, JobStatus
from src.splitter import get_splitter
from src.utils.file_utils import (
    get_output_dir, is_supported, is_media_file, is_video_file, human_size
)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")

# UI scaling for layout (keep at 1.0 to preserve default window size)
UI_SCALE = 1.0

# 選擇系統 UI 字型以改善字體銳利度（Windows 上偏好微軟正黑或 Segoe UI）
if platform.system() == "Windows":
    # Traditional Chinese Windows 會有 Microsoft JhengHei UI；若不存在，回退到 Segoe UI
    FONT_FAMILY = "Microsoft JhengHei UI"
    # 在某些系統上名稱可能不同，準備備援
    _try_fallback = False
else:
    FONT_FAMILY = "Segoe UI"

_STATUS_COLOR = {
    JobStatus.PENDING: ("gray60", "gray40"),
    JobStatus.RUNNING: ("cyan", "cyan"),
    JobStatus.DONE: ("green2", "green2"),
    JobStatus.ERROR: ("#FF6B6B", "#FF6B6B"),
}

_STATUS_TEXT = {
    JobStatus.PENDING: "等待中",
    JobStatus.RUNNING: "切分中…",
    JobStatus.DONE: "完成",
    JobStatus.ERROR: "錯誤",
}


class FileRow(ctk.CTkFrame):
    def __init__(self, master, job: SplitJob, **kwargs):
        scale = UI_SCALE
        cr = max(1, int(round(10 * scale)))
        super().__init__(master, corner_radius=cr, border_width=1, border_color=("gray80", "gray25"), **kwargs)
        self.job = job
        self.columnconfigure(1, weight=1)

        # 第一行：檔名 + 大小 + 選項
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(10, 6))
        name_frame.columnconfigure(0, weight=1)

        self._name_lbl = ctk.CTkLabel(
            name_frame, text=job.source_path.name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(8, int(round(13 * scale))), weight="bold"),
            anchor="w",
        )
        self._name_lbl.grid(row=0, column=0, sticky="w")

        size_bytes = job.source_path.stat().st_size if job.source_path.exists() else 0
        self._size_lbl = ctk.CTkLabel(
            name_frame, text=human_size(size_bytes),
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(8, int(round(11 * scale)))),
            text_color=("gray50", "gray60"),
        )
        self._size_lbl.grid(row=0, column=1, sticky="e", padx=(12, 0))

        if is_video_file(job.source_path):
            self._m4a_var = ctk.BooleanVar(value=False)
            self._m4a_cb = ctk.CTkCheckBox(
                name_frame, text="轉換為 m4a",
                variable=self._m4a_var,
                command=self._toggle_m4a,
                font=ctk.CTkFont(family=FONT_FAMILY, size=max(8, int(round(11 * scale)))),
            )
            self._m4a_cb.grid(row=0, column=2, padx=(12, 0), sticky="e")
        else:
            self._m4a_var = None
            self._m4a_cb = None

        # 第二行：進度條 + 狀態
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)

        self._progress = ctk.CTkProgressBar(progress_frame, height=max(4, int(round(6 * scale))), corner_radius=max(1, int(round(3 * scale))))
        self._progress.set(0)
        self._progress.grid(row=0, column=0, sticky="ew")

        self._status_lbl = ctk.CTkLabel(
            progress_frame, text="等待中",
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(8, int(round(10 * scale)))),
            text_color=("gray50", "gray60"),
            width=70,
            anchor="e",
        )
        self._status_lbl.grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.grid_columnconfigure(0, weight=1)

    def _toggle_m4a(self) -> None:
        if self._m4a_var is not None:
            self.job.convert_to_m4a = self._m4a_var.get()

    # ── 回呼（從工作執行緒呼叫，需透過 after 切回主執行緒）──

    def update_status(self, text: str) -> None:
        self.after(0, lambda: self._status_lbl.configure(
            text=text,
            text_color=("cyan", "cyan"),
        ))

    def update_progress(self, value: float) -> None:
        self.after(0, lambda: self._progress.set(value))
        self.after(0, lambda: self._status_lbl.configure(
            text=f"{int(value * 100)}%",
            text_color=("cyan", "cyan"),
        ))

    def mark_done(self, parts: int) -> None:
        self.after(0, lambda: self._progress.set(1.0))
        self.after(0, lambda: self._status_lbl.configure(
            text=f"完成（{parts} 個）",
            text_color=("green2", "green2"),
        ))

    def mark_error(self, msg: str) -> None:
        self.after(0, lambda: self._status_lbl.configure(
            text="錯誤",
            text_color=("#FF6B6B", "#FF6B6B"),
        ))
        self.after(0, lambda: self._progress.configure(progress_color="#FF6B6B"))


class DropZone(ctk.CTkFrame):
    """可拖放檔案的區域，或點擊觸發選擇對話框。"""

    def __init__(self, master, on_files, **kwargs):
        scale = UI_SCALE
        super().__init__(master, corner_radius=max(4, int(round(14 * scale))), border_width=2, **kwargs)
        self._on_files = on_files

        # 內容框架
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=20, pady=20)

        # 圖標
        icon_lbl = ctk.CTkLabel(
            content,
            text="📁",
            font=(FONT_FAMILY, max(18, int(round(48 * scale)))),
        )
        icon_lbl.pack(pady=(0, 8))

        # 主文字
        self._label = ctk.CTkLabel(
            content,
            text="拖放檔案 / 資料夾到此處",
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(10, int(round(15 * scale))), weight="bold"),
        )
        self._label.pack()

        # 次級文字
        sub_lbl = ctk.CTkLabel(
            content,
            text="或點擊選擇檔案",
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(8, int(round(12 * scale)))),
            text_color=("gray50", "gray60"),
        )
        sub_lbl.pack(pady=(4, 0))

        self.bind("<Button-1>", self._click)
        self._label.bind("<Button-1>", self._click)
        icon_lbl.bind("<Button-1>", self._click)
        sub_lbl.bind("<Button-1>", self._click)

        if _HAS_DND:
            self.drop_target_register(dnd.DND_FILES)  # type: ignore[attr-defined]
            self.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]

    def _click(self, _event=None):
        paths = filedialog.askopenfilenames(
            title="選擇要切分的檔案",
            filetypes=[
                ("支援的格式", "*.mp3 *.mp4 *.wav *.m4a *.aac *.flac *.ogg *.mkv "
                              "*.mov *.avi *.webm *.wma *.opus *.txt *.md"),
                ("音訊/影片", "*.mp3 *.mp4 *.wav *.m4a *.aac *.flac *.ogg "
                              "*.mkv *.mov *.avi *.webm *.wma *.opus"),
                ("文字檔", "*.txt *.md"),
                ("所有檔案", "*.*"),
            ],
        )
        if paths:
            self._on_files([Path(p) for p in paths])

    def _on_drop(self, event):
        # tkinterdnd2 回傳的路徑列表（可能含空格，用 {} 包裹）
        raw = event.data
        paths: list[Path] = []
        # 解析 {path with spaces} 和 plain/path 兩種格式
        import re
        for m in re.finditer(r'\{([^}]+)\}|(\S+)', raw):
            p = m.group(1) or m.group(2)
            paths.append(Path(p))
        if paths:
            self._on_files(paths)


class App(ctk.CTk if not _HAS_DND else dnd.Tk):  # type: ignore[misc]
    def __init__(self):
        super().__init__()
        self.title("NotebookLM 檔案切分工具")
        # 保持預設視窗大小（不要乘上 NB_SCALING），避免佔滿整個螢幕
        ui_scale = UI_SCALE
        geom_w = max(600, int(round(750 * ui_scale)))
        geom_h = max(480, int(round(620 * ui_scale)))
        self.geometry(f"{geom_w}x{geom_h}")
        self.minsize(max(500, int(round(650 * ui_scale))), max(400, int(round(500 * ui_scale))))

        if _HAS_DND:
            # 套用 CTk 主題到 tkinterdnd2 的 Tk 視窗
            ctk.set_appearance_mode("System")

        self._jobs: list[SplitJob] = []
        self._rows: dict[int, FileRow] = {}   # id(job) → FileRow
        self._lock = threading.Lock()

        self._build_ui()

    # ── UI 建構 ──────────────────────────────────────────────

    def _build_ui(self):
        # 使用 UI_SCALE（1.0）來維持預設版面大小與間距
        scale = UI_SCALE
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # 頂部標題
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        header.columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            header, text="NotebookLM 檔案切分工具",
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(14, int(round(18 * scale))), weight="bold"),
            text_color=("gray20", "gray80"),
            anchor="w"
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        # 拖放區
        self._drop_zone = DropZone(
            self, on_files=self._add_files,
            fg_color=("gray92", "gray14"),
            border_color=("gray70", "gray30"),
            height=max(100, int(round(140 * scale))),
        )
        self._drop_zone.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))

        # 工作清單（可捲動）
        self._list_label = ctk.CTkLabel(
            self, text="待切分清單",
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(10, int(round(13 * scale))), weight="bold"),
            anchor="w"
        )
        self._list_label.grid(row=2, column=0, sticky="nw", padx=20, pady=(0, 10))

        self._scroll = ctk.CTkScrollableFrame(self, label_text="", corner_radius=10)
        self._scroll.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self._scroll.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._empty_lbl = ctk.CTkLabel(
            self._scroll, text="尚未加入任何檔案",
            text_color=("gray60", "gray50"), font=ctk.CTkFont(family=FONT_FAMILY, size=max(8, int(round(12 * scale)))),
        )
        self._empty_lbl.grid(row=0, column=0, pady=40)

        # 底部工具列
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 16))
        bottom.columnconfigure(1, weight=1)

        self._clear_btn = ctk.CTkButton(
            bottom, text="清除完成項目", width=120,
            fg_color=("gray75", "gray25"),
            hover_color=("gray70", "gray20"),
            text_color=("gray20", "gray80"),
            border_width=0,
            corner_radius=max(6, int(round(8 * scale))),
            command=self._clear_done,
        )
        self._clear_btn.grid(row=0, column=0, padx=(0, 10))

        self._out_lbl = ctk.CTkLabel(
            bottom, text="📁 輸出：output/{日期}/{檔名}/",
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(8, int(round(11 * scale)))),
            text_color=("gray50", "gray60"),
            anchor="w",
        )
        self._out_lbl.grid(row=0, column=1, sticky="w")

        self._open_btn = ctk.CTkButton(
            bottom, text="開啟資料夾", width=100,
            fg_color=("gray75", "gray25"),
            hover_color=("gray70", "gray20"),
            text_color=("gray20", "gray80"),
            border_width=0,
            corner_radius=max(6, int(round(8 * scale))),
            command=self._open_output,
        )
        self._open_btn.grid(row=0, column=2, padx=(8, 8))

        self._start_btn = ctk.CTkButton(
            bottom, text="▶ 開始切分", width=110,
            font=ctk.CTkFont(family=FONT_FAMILY, size=max(9, int(round(12 * scale))), weight="bold"),
            corner_radius=max(6, int(round(8 * scale))),
            command=self._start_all,
        )
        self._start_btn.grid(row=0, column=3, padx=(0, 0))

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
            messagebox.showwarning(
                "不支援的檔案",
                "以下檔案格式不支援，已略過：\n" + "\n".join(unsupported[:10]),
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
        # 清空捲動區再重新渲染
        for widget in self._scroll.winfo_children():
            widget.destroy()
        self._rows.clear()

        if not self._jobs:
            self._empty_lbl = ctk.CTkLabel(
                self._scroll, text="尚未加入任何檔案",
                text_color=("gray60", "gray50"), font=ctk.CTkFont(size=12),
            )
            self._empty_lbl.grid(row=0, column=0, pady=40)
            return

        for idx, job in enumerate(self._jobs):
            row = FileRow(self._scroll, job, fg_color=("gray88", "gray16"))
            row.grid(row=idx, column=0, sticky="ew", pady=4)
            self._rows[id(job)] = row

            # 若已有狀態（重新整理後還原進度顯示）
            if job.status == JobStatus.DONE:
                row.mark_done(job.parts_count)
            elif job.status == JobStatus.ERROR:
                row.mark_error(job.error_msg or "")
            elif job.status == JobStatus.RUNNING:
                row.update_progress(job.progress)

    def _clear_done(self) -> None:
        with self._lock:
            self._jobs = [j for j in self._jobs if j.status != JobStatus.DONE]
        self._refresh_list()

    # ── 切分執行 ─────────────────────────────────────────────

    def _start_all(self) -> None:
        pending = [j for j in self._jobs if j.status == JobStatus.PENDING]
        if not pending:
            messagebox.showinfo("提示", "沒有等待切分的檔案。")
            return

        for job in pending:
            row = self._rows.get(id(job))
            if row is None:
                continue
            job.on_progress = row.update_progress
            job.on_done = row.mark_done
            job.on_error = row.mark_error
            job.on_status = row.update_status
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
            row = self._rows.get(id(job))
            if row:
                row.mark_error(str(exc))

    # ── 輸出資料夾 ───────────────────────────────────────────

    def _open_output(self) -> None:
        out = Path("output")
        if not out.exists():
            messagebox.showinfo("提示", "output 資料夾尚未建立，請先執行切分。")
            return
        os.startfile(str(out.resolve()))
