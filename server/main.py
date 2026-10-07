from __future__ import annotations

from asyncio import sleep
import asyncio
import os
from pathlib import Path
from queue import Queue, Full, Empty
from typing import TYPE_CHECKING
import firebase.realtime_db  as rtdb
from camera.http_cam import HTTPCam
import cv2
import numpy as np
from superdator_client import InferenceClient


if __package__:
    # Package import (``python -m server.main``).
    from .logger.logger import Logger
else:
    # Script import (``python server/main.py``).
    from logger.logger import Logger

if TYPE_CHECKING:
    from camera.structure.frame import CameraFrame

raw_frame_q : Queue[CameraFrame] = Queue(maxsize=1)
processed_frame_q: Queue[np.ndarray] = Queue(maxsize=1)

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
        processed_frame_q.put_nowait(frame.data)
    except Full:
        try:
            _ = processed_frame_q.get_nowait()
        except Empty:
            pass
        try:
            processed_frame_q.put_nowait(frame.data)
        except Full:
            pass

def handle_camera_frame(frame: CameraFrame) -> None:
    show_frame(frame)

def on_frame(frame: np.ndarray) -> None:
    """Queue annotated frames; OpenCV GUI calls stay on the main thread."""
    try:
        processed_frame_q.put_nowait(frame)
    except Full:
        try:
            processed_frame_q.get_nowait()
        except Empty:
            pass
        try:
            processed_frame_q.put_nowait(frame)
        except Full:
            pass

def main() -> None:
    

    fb = rtdb.FirebaseRealtimeHandler(
                    cred_path=str(Path(__file__).with_name(os.getenv("FIREBASE_API_KEY"))),
                    database_url=str(os.getenv("FIREBASE_RDB_URL")),
                )
    # fb.set("TotalFrames", 0)

    logger = Logger.get()
    cam = HTTPCam()
    camera_url = os.getenv("CAM_URL")
    if not camera_url:
        raise RuntimeError("Camera URL not set in environment variables")

    # try:
    cam.on_frame.subscribe(handle_camera_frame)
    if not cam.start_stream(camera_url):
        raise RuntimeError(f"Unable to open camera stream: {camera_url}")
    logger.info("Camera stream started. Press Ctrl+C to stop.")


    with InferenceClient(
        "wss://lego-inference.spetsen.se/stream",
        on_frame=on_frame,
    ) as client:
        try:
            while True:
                try:
                    camera_frame = raw_frame_q.get(timeout=0.1)
                except Empty:
                    camera_frame = None

                if camera_frame is not None:
                    # Frames must be OpenCV-style BGR NumPy arrays.
                    client.send(camera_frame.data)

                try:
                    annotated_frame = processed_frame_q.get_nowait()
                except Empty:
                    annotated_frame = None
                if annotated_frame is not None:
                    cv2.imshow("Inference result", annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cam.stop_stream()
            cv2.destroyAllWindows()
        # total_frames = 0

        # while True:
        #     try:
        #         raw_frame = raw_frame_q.get_nowait()
        #         cv2.imshow("Raw Frame", raw_frame.data)
        #     except Empty:
        #         pass

        #     # waitKey both keeps the OpenCV window responsive and lets the
        #     # user stop the stream without relying on Ctrl+C.
        #     if cv2.waitKey(1) & 0xFF == ord("q"):
        #         break

        #     fb.set("TotalFrames", float(fb.read("TotalFrames")) + total_frames)
        #     print(f"Total frames processed: {total_frames}")
        #     print(f"{fb.read('TotalFrames')} frames in total in the database.")
        #     total_frames += 1


    # except KeyboardInterrupt:
    #     logger.info("Stopping camera stream...")
    # finally:
    #     cam.stop_stream()
    #     cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError(
            "python-dotenv is missing. Install the project dependencies."
        ) from exc

    load_dotenv(Path(__file__).with_name(".env"))
    main()
