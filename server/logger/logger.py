from __future__ import annotations
from dataclasses import dataclass
from queue import Queue
import threading
import asyncio


@dataclass(frozen=True)
class LogMessage:
    level: str
    message: str

class LogInterface:
    def write(self, message: LogMessage) -> None:
        raise NotImplementedError("Must implement write method")


class ConsoleLogInterface(LogInterface):
    """Writes log messages to the process console."""

    def write(self, message: LogMessage) -> None:
        print(f"[{message.level.upper()}] {message.message}", flush=True)


class Logger:
    """
    Usage:
        logger = Logger.get()
        logger.info("This is an info message")

    Alternatively:
        Logger.get().info("This is an info message")
    """
    _instance: "Logger | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self.q: Queue[LogMessage | None] = Queue()
        self._log_debug: bool = False

        self._interfaces: list[LogInterface] = [ConsoleLogInterface()]
        self._interfaces_lock = threading.Lock()

        # Prevents unknowing logging after close 
        self._closed = False
        self._closed_lock = threading.Lock()

        self._loop: asyncio.AbstractEventLoop | None = None

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @classmethod # ALWAYS use this to get the logger instance
    def get(cls) -> "Logger":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def set_log_debug(self, debug: bool) -> None:
        self._log_debug = debug

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # "quick loggers"
    def log(self, level: str, message: str) -> None:
        with self._closed_lock:
            if self._closed:
                raise RuntimeError("Cannot log to closed Logger")
        self.q.put(LogMessage(level, message))
            
    def debug(self, message: str) -> None:
        if self._log_debug:
            self.log("debug", message)

    def info(self, message: str) -> None:
        self.log("info", message)

    def warning(self, message: str) -> None:
        self.log("warning", message)

    def error(self, message: str) -> None:
        self.log("error", message)

    def close(self) -> None:
        with self._closed_lock:
            self._closed = True
        self.q.put(None)
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while True:
            msg = self.q.get()
            if msg is None:
                break
            self._write_out(msg)

    def _write_out(self, message: LogMessage) -> None:
        with self._interfaces_lock:
            interfaces = list(self._interfaces)  # snapshot, prevents threading bs
        assert interfaces, "No log interfaces available!"
        for interface in interfaces:
            interface.write(message)
            # asyncio.run(send_log_message(message))



    def add_interface(self, interface: LogInterface) -> None:
        with self._interfaces_lock:
            self._interfaces.append(interface)
