from __future__ import annotations
import cv2
import threading
import time
from camera.camera import Camera
from camera.structure.frame import CameraFrame
from logger.logger import Logger

class HTTPCam(Camera):
    def __init__(self) -> None:
        super().__init__()
        self._cap: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._frame_counter = 0
        
    def start_stream(self, url: str) -> None:
        if self._cap is not None:
            Logger.get().warning("start_stream() called but stream is already running")
            return
        self._cap = cv2.VideoCapture(url)
        if not self._cap.isOpened():
            Logger.get().error(f"Failed to open video stream from URL: {url}")
            self._cap = None
            return
        
        self._stop_event.clear()
        
        # Daemon thread kills performance (from testing)
        self._thread = threading.Thread(target=self._loop, daemon=False)
        self._thread.start()
        
    def _loop(self) -> None:
        log = Logger.get()
        
        if self._cap is None:
            log.error("Video capture not initialized")
            return
        

        try:
            while not self._stop_event.is_set():
                ret, frame = self._cap.read()
                if not ret:
                    log.warning("Frame not received")
                    time.sleep(0.1)
                    continue
                
                height, width, _ = frame.shape
                camera_frame = CameraFrame(
                    data=frame,
                    width=width,
                    height=height,
                    image_format='bgr8',
                    id=self._frame_counter
                )
                self.on_frame.emit(camera_frame)
                self._frame_counter += 1
        except Exception as ex:
            log.error(f"Error in camera loop: {ex}")    
        finally:
            # Cleanup
            self._stop_event.set()
            try:
                self._cap.release()
            except Exception as ex:
                log.error(f"Error releasing video capture: {ex}")   
            self._cap = None
            log.info("Camera loop stopped")
    
    def stop_stream(self) -> None:
        if self._cap is None:
            Logger.get().warning("stop_stream() called but stream is not running")
            return
        
        self._stop_event.set()
        
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                Logger.get().warning("Camera thread did not terminate within timeout")
        self._thread = None
        
        if self._cap is not None: # type: ignore (typehint is bs) 
            self._cap.release()
            self._cap = None
