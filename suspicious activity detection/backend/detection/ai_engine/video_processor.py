"""
Video Processing Module.
Handles video reading, writing, and the frame-by-frame processing loop.
Produces annotated MP4 output with bounding boxes and timestamps.
"""
import logging
import os
import threading
import time
import uuid
from datetime import datetime

import cv2
import numpy as np

from django.conf import settings

logger = logging.getLogger('detection')


class VideoProcessor:
    """
    Processes video files or live streams frame-by-frame.
    Produces annotated MP4 files with bounding boxes and timestamps.
    """

    def __init__(self, pipeline=None):
        """
        Args:
            pipeline: SurveillancePipeline instance
        """
        self.pipeline = pipeline
        self.is_recording = False
        self._writer = None
        self._writer_lock = threading.Lock()
        self._current_output_path = None

    def start_recording(self, output_dir=None, fps=24, width=640, height=480):
        """
        Start recording processed video to an MP4 file.

        Args:
            output_dir: directory to save the output file
            fps: frames per second
            width: frame width
            height: frame height

        Returns:
            str: output file path
        """
        if output_dir is None:
            output_dir = str(settings.VIDEO_STORAGE.get(
                'LIVE_RECORDINGS',
                settings.MEDIA_ROOT / 'live_recordings'
            ))

        os.makedirs(output_dir, exist_ok=True)

        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(output_dir, filename)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        with self._writer_lock:
            self._writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            self._current_output_path = output_path
            self.is_recording = True

        logger.info(f"Started recording to {output_path}")
        return output_path

    def stop_recording(self):
        """Stop the current recording and finalize the MP4 file."""
        with self._writer_lock:
            if self._writer:
                self._writer.release()
                self._writer = None
            self.is_recording = False
            path = self._current_output_path
            self._current_output_path = None

        logger.info(f"Stopped recording. File saved: {path}")
        return path

    def write_frame(self, frame):
        """Write an annotated frame to the output video."""
        with self._writer_lock:
            if self._writer and self.is_recording:
                self._writer.write(frame)

    def process_uploaded_video(self, input_path, output_dir=None, progress_callback=None,
                               process_every_n=3):
        """
        Process an uploaded video file through the AI pipeline.
        Produces an annotated MP4 with bounding boxes and timestamps.

        Uses frame skipping: only runs AI on every Nth frame, writes all frames
        with cached annotations for smooth playback.

        Args:
            input_path: path to the input video file
            output_dir: directory for the output file
            progress_callback: optional callback(current_frame, total_frames)
            process_every_n: run AI pipeline every N frames (default 3)

        Returns:
            dict with output_path, total_frames, detections, duration, fps, etc.
        """
        if output_dir is None:
            output_dir = str(settings.VIDEO_STORAGE.get(
                'PROCESSED_VIDEOS',
                settings.MEDIA_ROOT / 'processed_videos'
            ))

        os.makedirs(output_dir, exist_ok=True)

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 24
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_filename = f"{base_name}_processed_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        all_detections = []
        frame_number = 0
        last_result = None

        # Reset pipeline windows for fresh processing
        self.pipeline.reset_windows()

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_number += 1

                # Only run full AI pipeline every Nth frame
                if frame_number % process_every_n == 1 or process_every_n <= 1:
                    result = self.pipeline.process_frame(frame, frame_number=frame_number)
                    last_result = result
                else:
                    # Use cached result — just re-annotate this frame with last detections
                    if last_result:
                        result = {
                            'annotated_frame': self.pipeline._annotate_frame(
                                frame.copy(), last_result['detections'], last_result['timestamp']
                            ),
                            'detections': last_result['detections'],
                            'timestamp': last_result['timestamp'],
                            'frame_number': frame_number,
                        }
                    else:
                        result = {
                            'annotated_frame': frame,
                            'detections': [],
                            'timestamp': '',
                            'frame_number': frame_number,
                        }

                annotated = result['annotated_frame']
                if annotated.shape[1] != width or annotated.shape[0] != height:
                    annotated = cv2.resize(annotated, (width, height))
                writer.write(annotated)

                # Only collect new detections from frames we actually processed
                if frame_number % process_every_n == 1 or process_every_n <= 1:
                    for det in result['detections']:
                        all_detections.append(det)

                if progress_callback and frame_number % 30 == 0:
                    progress_callback(frame_number, total_frames)

        finally:
            cap.release()
            writer.release()

        duration = total_frames / fps if fps > 0 else 0

        logger.info(
            f"Video processing complete: {frame_number} frames, "
            f"{len(all_detections)} detections, saved to {output_path}"
        )

        return {
            'output_path': output_path,
            'total_frames': frame_number,
            'detections': all_detections,
            'duration': round(duration, 2),
            'fps': fps,
            'width': width,
            'height': height
        }


class LiveStreamManager:
    """
    Manages live streaming sessions.
    Handles frame buffering and real-time processing coordination.
    """

    def __init__(self):
        self.sessions = {}  # session_id -> session data
        self._lock = threading.Lock()

    def create_session(self, pipeline):
        """Create a new live streaming session."""
        session_id = uuid.uuid4().hex[:12]
        processor = VideoProcessor(pipeline=pipeline)

        with self._lock:
            self.sessions[session_id] = {
                'id': session_id,
                'processor': processor,
                'created_at': datetime.now(),
                'frame_count': 0,
                'active': True,
                'recording_path': None,
            }

        logger.info(f"Created live session: {session_id}")
        return session_id

    def get_session(self, session_id):
        """Get a session by ID."""
        with self._lock:
            return self.sessions.get(session_id)

    def close_session(self, session_id):
        """Close and cleanup a session."""
        with self._lock:
            session = self.sessions.pop(session_id, None)
            if session and session['processor'].is_recording:
                session['processor'].stop_recording()

        logger.info(f"Closed session: {session_id}")
        return session

    def get_active_sessions(self):
        """Get all active sessions."""
        with self._lock:
            return {
                sid: {
                    'id': s['id'],
                    'created_at': s['created_at'].isoformat(),
                    'frame_count': s['frame_count'],
                    'active': s['active']
                }
                for sid, s in self.sessions.items()
                if s['active']
            }


# Singleton instances
_stream_manager = None


def get_stream_manager():
    """Get the singleton LiveStreamManager."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = LiveStreamManager()
    return _stream_manager
