# pylint: disable=consider-using-with
from __future__ import annotations
import traceback
from typing import Any, Callable, Iterable, List, TypeVar
from contextlib import AbstractContextManager

from .logs import log_warning
from .singleton import Singleton

_T = TypeVar("_T")


class Scheduler(Singleton, AbstractContextManager):
    """
    Worker that wraps task scheduling.
    No multiprocessing/threading pools -- sequential execution is significantly faster
    for small GIL-bound Python crypto tasks (especially on Windows where process
    spawning adds 1-2s overhead per pool creation).
    """

    def __init__(self) -> None:
        super().__init__()

    def __enter__(self) -> Scheduler:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        pass

    def close(self) -> None:
        """No-op: no pools to close."""
        pass

    @staticmethod
    def cpu_count() -> int:
        """Get CPU count"""
        try:
            from psutil import cpu_count
            return int(cpu_count(logical=False))
        except Exception:
            import os
            return os.cpu_count() or 1

    def schedule(
        self,
        task: Callable,
        arguments: Iterable[Iterable[Any]],
        with_shared_resources: bool = False,
    ) -> List[_T]:
        """
        Execute tasks sequentially (no pool overhead).
        with_shared_resources is ignored for API compatibility.
        """
        return [task(*args) for args in arguments]

    @staticmethod
    def safe_starmap(
        pool: Any, task: Callable, arguments: Iterable[Iterable[Any]]
    ) -> List[_T]:
        """Legacy method kept for API compatibility -- runs sequentially."""
        try:
            return [task(*args) for args in arguments]
        except Exception:
            log_warning(
                f"safe_starmap({task}) failed with \n {traceback.format_exc()}"
            )
            return []

    @staticmethod
    def safe_map(pool: Any, task: Callable, arguments: Iterable[Any]) -> List[_T]:
        """Legacy method kept for API compatibility -- runs sequentially."""
        try:
            return [task(arg) for arg in arguments]
        except Exception:
            log_warning(
                f"safe_map({task}) failed with \n {traceback.format_exc()}"
            )
            return []
