from __future__ import annotations

from logger.logger import Logger
from queue import Queue, Full, Empty
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from camera.structure.frame import CameraFrame

raw_frame_q : Queue[CameraFrame] = Queue(maxsize=1)
processed_frame_q : Queue[CameraFrame] = Queue(maxsize=1)

def show_frame(frame: CameraFrame) -> None:
    try:
        raw_frame_q.put_nowait(frame)
    except Full:
        try:
            _ = raw_frame_q.get_nowait()
        except Empty:
            pass
        try:
            raw_frame_q.put_nowait(frame)
        except Full:
            pass

def show_processed(frame: CameraFrame) -> None:
    try:
        processed_frame_q.put_nowait(frame)
    except Full:
        try:
            _ = processed_frame_q.get_nowait()
        except Empty:
            pass
        try:
            processed_frame_q.put_nowait(frame)
        except Full:
            pass

def handle_camera_frame(frame: CameraFrame) -> None:
    show_frame(frame)


def main() -> None:
    try:
        import cv2
        from camera.http_cam import HTTPCam
    except ImportError as exc:
        raise RuntimeError(
            "Camera dependencies are missing. Install numpy and opencv-python."
        ) from exc

    logger = Logger.get()
    cam = HTTPCam()
    camera_url = os.getenv("CAM_URL")
    if not camera_url:
        raise RuntimeError("Camera URL not set in environment variables")

    try:
        cam.on_frame.subscribe(handle_camera_frame)
        cam.start_stream(camera_url)
        logger.info("Camera stream started. Press Ctrl+C to stop.")

        while True:
            try:
                raw_frame = raw_frame_q.get_nowait()
                cv2.imshow("Raw Frame", raw_frame.data)
            except Empty:
                pass

            # waitKey both keeps the OpenCV window responsive and lets the
            # user stop the stream without relying on Ctrl+C.
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        logger.info("Stopping camera stream...")
    finally:
        cam.stop_stream()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError(
            "python-dotenv is missing. Install the project dependencies."
        ) from exc

    load_dotenv()
    main()
