from __future__ import annotations

import os
import threading
import time
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

def sender_loop(client: InferenceClient, stop_event: threading.Event, logger: Logger) -> None:
    """Send queued frames to the inference server on a dedicated thread.

    ``client.send`` is a blocking TCP write: if the server is slow or wedged,
    this thread simply blocks (which paces us to the server's rate), while the
    GUI thread keeps running. ``raw_frame_q`` is maxsize=1 with drop-oldest,
    so we always send the most recent frame.
    """
    deadline = time.monotonic() + 15.0
    while not client.connected and time.monotonic() < deadline:
        if stop_event.is_set():
            return
        time.sleep(0.2)
    if not client.connected:
        logger.warning("Inference server not connected yet; will keep trying")

    was_failing = False
    last_failure_log = 0.0
    while not stop_event.is_set():
        try:
            camera_frame = raw_frame_q.get(timeout=0.25)
        except Empty:
            continue
        if stop_event.is_set():
            return

        # Frames must be OpenCV-style BGR NumPy arrays.
        if client.send(camera_frame.data):
            if was_failing:
                logger.info("Inference server reachable again, resending frames")
                was_failing = False
            continue

        now = time.monotonic()
        if not was_failing or now - last_failure_log >= 5.0:
            logger.warning(
                f"Frame not sent to inference server (connected={client.connected})"
            )
            last_failure_log = now
        was_failing = True

def start_cam():
    cam = HTTPCam()
    camera_url = os.getenv("CAM_URL")
    logger = Logger.get()
    if not camera_url:
        raise RuntimeError("Camera URL not set in environment variables")

    # try:
    cam.on_frame.subscribe(handle_camera_frame)
    if not cam.start_stream(camera_url):
        raise RuntimeError(f"Unable to open camera stream: {camera_url}")
    logger.info("Camera stream started. Press Ctrl+C to stop.")
    return cam


def main() -> None:
    

    fb = rtdb.FirebaseRealtimeHandler(
                    cred_path=str(Path(__file__).with_name(os.getenv("FIREBASE_API_KEY"))), # type: ignore
                    database_url=str(os.getenv("FIREBASE_RDB_URL")),
                )
    # fb.set("TotalFrames", 0)

    logger = Logger.get()
    cam = start_cam()

    with InferenceClient(
        "wss://lego-inference.spetsen.se/stream",
        on_frame=on_frame,
    ) as client:
        sender_stop = threading.Event()
        sender = threading.Thread(
            target=sender_loop,
            args=(client, sender_stop, logger),
            name="inference-sender",
            daemon=True,
        )
        sender.start()
        try:
            while True:
                try:
                    annotated_frame = processed_frame_q.get(timeout=0.1)
                    if annotated_frame is not None:
                        detections = client.latest_detections
                        if detections:
                            logger.info(f"Detected: {[(d['name'], round(d['confidence'], 2)) for d in detections]}")
                        cv2.imshow("Inference result", annotated_frame)

                except Empty:
                    annotated_frame = None
                if annotated_frame is not None:
                    cv2.imshow("Inference result", annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            sender_stop.set()
            sender.join(timeout=2.0)
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
