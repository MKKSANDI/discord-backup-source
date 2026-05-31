"""Interactive loading dialog utilities."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Box, Frame

T = TypeVar("T")

_SPINNER_FRAMES = ["|", "/", "-", "\\"]
_STYLE = Style.from_dict(
    {
        # White + blue theme to match the main menu dialogs.
        "frame": "bg:#f7f9ff #0f172a",
        "title": "bg:#2563eb #ffffff bold",
        "text": "bg:#f7f9ff #0f172a",
        "spinner": "bg:#f7f9ff #2563eb bold",
    }
)


@dataclass
class ProgressHandle:
    update: Callable[[str], None]


class LoadingDialog(Generic[T]):
    """Display a modal loading spinner while executing a worker function."""

    def __init__(self, title: str, subtitle: str, worker: Callable[[ProgressHandle], T]):
        self.title = title
        self.subtitle = subtitle
        self.worker = worker

        self._result: Optional[T] = None
        self._error: Optional[BaseException] = None
        self._finished = False
        self._frame_index = 0
        self._status = subtitle

        self._status_control = FormattedTextControl(text=self._render_status)
        body = HSplit(
            [
                Window(height=1, char=" "),
                Window(content=self._status_control, height=3, style="class:text"),
                Window(height=1, char=" "),
            ]
        )
        framed = Frame(
            title=f" {self.title} ",
            body=Box(body=body, padding=1),
            style="class:frame",
        )
        self._dialog = framed

        kb = KeyBindings()

        @kb.add("escape")
        def _(_event) -> None:
            if not self._finished:
                return
            _event.app.exit(self._result)

        self._application = Application(
            layout=Layout(self._dialog),
            key_bindings=kb,
            full_screen=True,
            mouse_support=True,
            style=_STYLE,
        )

    def _render_status(self) -> list[tuple[str, str]]:
        spinner = _SPINNER_FRAMES[self._frame_index % len(_SPINNER_FRAMES)]
        line = f" {spinner} {self._status}"
        return [("class:spinner", line)]

    async def _animate(self) -> None:
        while not self._finished:
            self._frame_index += 1
            self._application.invalidate()
            await asyncio.sleep(0.12)

    async def _async_set_status(self, text: str) -> None:
        self._status = text
        self._application.invalidate()

    def run(self) -> T:
        loop_future: asyncio.Future[None] | None = None

        async def worker_coro() -> None:
            loop = asyncio.get_running_loop()

            def update(text: str) -> None:
                asyncio.run_coroutine_threadsafe(self._async_set_status(text), loop)

            try:
                result = await loop.run_in_executor(
                    None, lambda: self.worker(ProgressHandle(update=update))
                )
                self._result = result
            except BaseException as exc:  # noqa: BLE001
                self._error = exc
            finally:
                self._finished = True
                self._application.exit(result=self._result)

        def pre_run() -> None:
            self._application.create_background_task(self._animate())
            nonlocal loop_future
            loop_future = self._application.create_background_task(worker_coro())

        self._application.run(pre_run=pre_run)
        if loop_future is not None:
            loop_future.result()
        if self._error:
            raise self._error
        return self._result  # type: ignore[return-value]


def run_with_loading(title: str, subtitle: str, fn: Callable[[ProgressHandle], T]) -> T:
    dialog = LoadingDialog(title, subtitle, fn)
    return dialog.run()


__all__ = ["run_with_loading", "ProgressHandle"]
