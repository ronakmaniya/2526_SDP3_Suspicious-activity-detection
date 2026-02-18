"""
Django REST API Views for the Suspicious Activity Detection System.
Handles frame analysis, video upload, live sessions, and event retrieval.
"""
import base64
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime

import cv2
import numpy as np
from django.conf import settings
from django.http import FileResponse, StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DetectionEvent, VideoRecording
from .serializers import (
    DetectionEventSerializer,
    FrameAnalysisRequestSerializer,
    FrameAnalysisResponseSerializer,
    LiveSessionSerializer,
    VideoRecordingListSerializer,
    VideoRecordingSerializer,
    VideoUploadSerializer,
)

logger = logging.getLogger('detection')


def _get_pipeline():
    """Lazy-load the AI pipeline."""
    from .ai_engine.pipeline import get_pipeline
    ai_settings = getattr(settings, 'AI_MODELS', {})
    pipeline = get_pipeline(settings=ai_settings)
    if not pipeline._initialized:
        pipeline.initialize()
    return pipeline


def _get_stream_manager():
    """Get the stream manager."""
    from .ai_engine.video_processor import get_stream_manager
    return get_stream_manager()


class FrameAnalysisView(APIView):
    """
    POST /api/analyze-frame/
    Receives a single base64-encoded frame, processes it through the AI pipeline,
    and returns the annotated frame with detections.
    """

    def post(self, request):
        serializer = FrameAnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Decode base64 frame
            frame_data = serializer.validated_data['frame']

            # Remove data URL prefix if present
            if ',' in frame_data:
                frame_data = frame_data.split(',')[1]

            frame_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                return Response(
                    {'error': 'Invalid frame data'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Process through AI pipeline (skip annotation — frontend draws its own overlay)
            pipeline = _get_pipeline()
            result = pipeline.process_frame(frame, skip_annotation=True)

            # Save frame to active recording if session exists
            recording_id = serializer.validated_data.get('recording_id')
            session_id = serializer.validated_data.get('session_id', '')
            if recording_id and session_id:
                self._save_to_recording(result, session_id, frame)

            # Log suspicious detections to database
            for det in result['detections']:
                if det['activity_label'] == 'suspicious' and det['activity_confidence'] > 0.6:
                    DetectionEvent.objects.create(
                        label='suspicious',
                        confidence=det['activity_confidence'],
                        bounding_box={
                            'x1': det['bbox'][0],
                            'y1': det['bbox'][1],
                            'x2': det['bbox'][2],
                            'y2': det['bbox'][3],
                        },
                        frame_number=result['frame_number'],
                        recording_id=recording_id,
                    )

            # Format response (no annotated frame — frontend draws its own overlay)
            response_data = {
                'detections': [
                    {
                        'bbox': d['bbox'],
                        'detection_confidence': d['detection_confidence'],
                        'activity_label': d['activity_label'],
                        'activity_confidence': d['activity_confidence'],
                        'activity': d.get('activity', 'unknown'),
                        'person_id': d['person_id'],
                    }
                    for d in result['detections']
                ],
                'timestamp': result['timestamp'],
                'frame_number': result['frame_number'],
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Frame analysis error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _save_to_recording(self, result, session_id, raw_frame):
        """Save frame to active recording session."""
        try:
            stream_mgr = _get_stream_manager()
            session = stream_mgr.get_session(session_id)
            if session and session['processor'].is_recording:
                # Write raw frame (annotation is done on frontend)
                session['processor'].write_frame(raw_frame)
                session['frame_count'] += 1
        except Exception as e:
            logger.warning(f"Could not save frame to recording: {e}")


class LiveSessionView(APIView):
    """
    POST /api/live-session/
    Start or stop a live recording session.
    """

    def post(self, request):
        serializer = LiveSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action_type = serializer.validated_data['action']
        session_id = serializer.validated_data.get('session_id', '')

        try:
            stream_mgr = _get_stream_manager()
            pipeline = _get_pipeline()

            if action_type == 'start':
                # Create new session
                session_id = stream_mgr.create_session(pipeline)
                session = stream_mgr.get_session(session_id)

                # Start recording
                output_path = session['processor'].start_recording()
                session['recording_path'] = output_path

                # Create database record
                recording = VideoRecording.objects.create(
                    title=f"Live Recording {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    source_type='live',
                    status='recording',
                    processed_video_path=output_path,
                )

                # Reset pipeline for fresh session
                pipeline.reset_windows()

                return Response({
                    'session_id': session_id,
                    'recording_id': recording.id,
                    'status': 'recording',
                    'output_path': output_path,
                }, status=status.HTTP_201_CREATED)

            elif action_type == 'stop':
                if not session_id:
                    return Response(
                        {'error': 'session_id required for stop action'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                session = stream_mgr.get_session(session_id)
                if not session:
                    return Response(
                        {'error': 'Session not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                frame_count = session.get('frame_count', 0)
                output_path = session['processor'].stop_recording()
                stream_mgr.close_session(session_id)

                # Finalize the VideoRecording in the database
                recording_id = serializer.validated_data.get('recording_id')
                if recording_id:
                    try:
                        recording = VideoRecording.objects.get(id=recording_id)
                        recording.status = 'completed'
                        recording.total_frames = frame_count
                        if frame_count > 0:
                            recording.duration = round(frame_count / 24.0, 2)  # estimate at 24 fps
                        recording.save()
                    except VideoRecording.DoesNotExist:
                        logger.warning(f"Recording {recording_id} not found for finalization")

                return Response({
                    'session_id': session_id,
                    'status': 'stopped',
                    'output_path': output_path,
                    'total_frames': frame_count,
                })

        except Exception as e:
            logger.error(f"Live session error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """GET /api/live-session/ — list active sessions."""
        stream_mgr = _get_stream_manager()
        sessions = stream_mgr.get_active_sessions()
        return Response({'sessions': sessions})


class VideoUploadView(APIView):
    """
    POST /api/upload-video/
    Upload an MP4 video file for processing.
    Returns the processed annotated video.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = VideoUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        video_file = serializer.validated_data['video']
        title = serializer.validated_data.get('title', 'Uploaded Video')

        try:
            # Save uploaded file
            upload_dir = str(settings.VIDEO_STORAGE.get(
                'UPLOADED_VIDEOS',
                settings.MEDIA_ROOT / 'uploaded_videos'
            ))
            os.makedirs(upload_dir, exist_ok=True)

            filename = f"{uuid.uuid4().hex[:8]}_{video_file.name}"
            upload_path = os.path.join(upload_dir, filename)

            with open(upload_path, 'wb+') as dest:
                for chunk in video_file.chunks():
                    dest.write(chunk)

            # Create database record
            recording = VideoRecording.objects.create(
                title=title,
                source_type='upload',
                status='processing',
                original_video_path=upload_path,
            )

            # Process video in background thread
            thread = threading.Thread(
                target=self._process_video_async,
                args=(upload_path, recording.id),
                daemon=True
            )
            thread.start()

            return Response({
                'recording_id': recording.id,
                'status': 'processing',
                'message': 'Video uploaded and processing started.',
                'original_path': upload_path,
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Video upload error: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_video_async(self, input_path, recording_id):
        """Process uploaded video in a background thread."""
        try:
            from .ai_engine.video_processor import VideoProcessor
            pipeline = _get_pipeline()
            processor = VideoProcessor(pipeline=pipeline)

            result = processor.process_uploaded_video(input_path)

            # Update database record
            recording = VideoRecording.objects.get(id=recording_id)
            recording.status = 'completed'
            recording.processed_video_path = result['output_path']
            recording.duration = result['duration']
            recording.fps = result['fps']
            recording.total_frames = result['total_frames']
            recording.resolution_width = result['width']
            recording.resolution_height = result['height']

            # Count events
            suspicious_count = sum(
                1 for d in result['detections'] if d['activity_label'] == 'suspicious'
            )
            normal_count = sum(
                1 for d in result['detections'] if d['activity_label'] == 'normal'
            )
            recording.suspicious_count = suspicious_count
            recording.normal_count = normal_count
            recording.save()

            # Log detection events
            for det in result['detections']:
                if det['activity_label'] == 'suspicious' and det['activity_confidence'] > 0.6:
                    DetectionEvent.objects.create(
                        label='suspicious',
                        confidence=det['activity_confidence'],
                        bounding_box={
                            'x1': det['bbox'][0],
                            'y1': det['bbox'][1],
                            'x2': det['bbox'][2],
                            'y2': det['bbox'][3],
                        },
                        frame_number=det['frame_number'],
                        recording=recording,
                        video_path=result['output_path'],
                    )

            logger.info(f"Video processing complete for recording {recording_id}")

        except Exception as e:
            logger.error(f"Async video processing failed: {e}", exc_info=True)
            try:
                recording = VideoRecording.objects.get(id=recording_id)
                recording.status = 'failed'
                recording.save()
            except Exception:
                pass


class DetectionEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/events/ — list all detection events
    GET /api/events/{id}/ — retrieve a specific event
    """
    queryset = DetectionEvent.objects.all()
    serializer_class = DetectionEventSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by label
        label = self.request.query_params.get('label')
        if label:
            queryset = queryset.filter(label=label)

        # Filter by recording
        recording_id = self.request.query_params.get('recording_id')
        if recording_id:
            queryset = queryset.filter(recording_id=recording_id)

        # Filter by minimum confidence
        min_confidence = self.request.query_params.get('min_confidence')
        if min_confidence:
            queryset = queryset.filter(confidence__gte=float(min_confidence))

        return queryset


class VideoRecordingViewSet(viewsets.ModelViewSet):
    """
    GET /api/recordings/ — list all recordings
    GET /api/recordings/{id}/ — retrieve a specific recording with events
    DELETE /api/recordings/{id}/ — delete a recording and its video files
    """
    queryset = VideoRecording.objects.all()
    http_method_names = ['get', 'delete', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        """Delete a recording, its associated events, and video files from disk."""
        recording = self.get_object()

        # Delete video files from disk
        for path_field in [recording.original_video_path, recording.processed_video_path]:
            if path_field and os.path.exists(path_field):
                try:
                    os.remove(path_field)
                    logger.info(f"Deleted video file: {path_field}")
                except OSError as e:
                    logger.warning(f"Could not delete file {path_field}: {e}")

        # Delete associated detection events
        DetectionEvent.objects.filter(recording=recording).delete()

        # Delete the database record
        recording.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if self.action == 'list':
            return VideoRecordingListSerializer
        return VideoRecordingSerializer

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """GET /api/recordings/{id}/download/ — download processed video."""
        recording = self.get_object()
        video_path = recording.processed_video_path

        if not video_path or not os.path.exists(video_path):
            return Response(
                {'error': 'Processed video not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return FileResponse(
            open(video_path, 'rb'),
            content_type='video/mp4',
            as_attachment=True,
            filename=os.path.basename(video_path)
        )

    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """GET /api/recordings/{id}/status_check/ — check processing status."""
        recording = self.get_object()
        return Response({
            'id': recording.id,
            'status': recording.status,
            'total_frames': recording.total_frames,
            'suspicious_count': recording.suspicious_count,
            'normal_count': recording.normal_count,
        })


@api_view(['GET'])
def health_check(request):
    """GET /api/health/ — system health check."""
    return Response({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
    })


@api_view(['GET'])
def system_stats(request):
    """GET /api/stats/ — system statistics."""
    total_events = DetectionEvent.objects.count()
    suspicious_events = DetectionEvent.objects.filter(label='suspicious').count()
    total_recordings = VideoRecording.objects.count()
    active_recordings = VideoRecording.objects.filter(status='recording').count()

    return Response({
        'total_events': total_events,
        'suspicious_events': suspicious_events,
        'normal_events': total_events - suspicious_events,
        'total_recordings': total_recordings,
        'active_recordings': active_recordings,
        'timestamp': datetime.now().isoformat(),
    })
