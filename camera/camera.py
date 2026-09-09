# This is a default interface for camera modules
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Awaitable, Callable, Generic, TypeVar
import asyncio
import inspect

if TYPE_CHECKING:
    from .structure.frame import CameraFrame


# Subscribable event system for camera frames
T = TypeVar("T")
class Event(Generic[T]):
    def __init__(self) -> None:
        self._subs: list[Callable[[T], None | Awaitable[None]]] = []
    
    def subscribe(self, fn: Callable[[T], None | Awaitable[None]]) -> None:
        if fn not in self._subs:
            self._subs.append(fn)
    
    def unsubscribe(self, fn: Callable[[T], None | Awaitable[None]]) -> None:
        if fn in self._subs:
            self._subs.remove(fn)
    
    def emit(self, value: T) -> None:
        for fn in list(self._subs):
            result = fn(value)
            if inspect.isawaitable(result):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # ``emit`` may be called from a camera worker thread.
                    # There is no event loop there, so finish the callback
                    # instead of leaking the coroutine or raising an error.
                    asyncio.run(result)
                else:
                    loop.create_task(result)

class Camera(ABC):
    def __init__(self) -> None:
        self.on_frame: Event[CameraFrame] = Event()
    
    @abstractmethod
    def start_stream(self, url: str) -> None:
        """Start the camera stream from the given URL."""
        raise NotImplementedError("start_stream method not implemented")

    @abstractmethod
    def stop_stream(self) -> None:
        """Stop the camera stream."""
        raise NotImplementedError("stop_stream method not implemented")
    
