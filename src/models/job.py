from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class SplitJob:
    source_path: Path
    output_dir: Path
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    parts_count: int = 0
    error_msg: Optional[str] = None
    convert_to_m4a: bool = False
    on_progress: Optional[Callable[[float], None]] = field(default=None, repr=False)
    on_done: Optional[Callable[[int], None]] = field(default=None, repr=False)
    on_error: Optional[Callable[[str], None]] = field(default=None, repr=False)
