from __future__ import annotations

from typing import Protocol


class ProgressHandle(Protocol):
    def update(self, message: str) -> None: ...


def run_with_loading(
    title: str,
    message: str,
    worker: object,
) -> object:
    """Run a worker with a loading indicator. Worker receives one argument: update(message)."""
    def noop_update(msg: str) -> None:
        pass
    if callable(worker):
        return worker(noop_update)
    return None


__all__ = ["ProgressHandle", "run_with_loading"]
