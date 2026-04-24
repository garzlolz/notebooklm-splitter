from abc import ABC, abstractmethod
from src.models.job import SplitJob


class BaseSplitter(ABC):
    SUPPORTED_EXTENSIONS: set[str] = set()

    @abstractmethod
    def split(self, job: SplitJob) -> None: ...

    @classmethod
    def can_handle(cls, ext: str) -> bool:
        return ext.lower() in cls.SUPPORTED_EXTENSIONS
