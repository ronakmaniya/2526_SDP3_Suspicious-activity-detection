"""
Serializers for the Suspicious Activity Detection System.
"""
from rest_framework import serializers
from .models import DetectionEvent, VideoRecording


class DetectionEventSerializer(serializers.ModelSerializer):
    """Serializer for detection events."""

    class Meta:
        model = DetectionEvent
        fields = [
            'id', 'timestamp', 'label', 'confidence',
            'video_path', 'duration', 'bounding_box',
            'frame_number', 'recording', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class VideoRecordingSerializer(serializers.ModelSerializer):
    """Serializer for video recordings."""
    events = DetectionEventSerializer(many=True, read_only=True)
    suspicious_percentage = serializers.ReadOnlyField()

    class Meta:
        model = VideoRecording
        fields = [
            'id', 'title', 'source_type', 'status',
            'original_video_path', 'processed_video_path',
            'duration', 'fps', 'resolution_width', 'resolution_height',
            'total_frames', 'suspicious_count', 'normal_count',
            'suspicious_percentage', 'events', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VideoRecordingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing recordings (without events)."""
    suspicious_percentage = serializers.ReadOnlyField()

    class Meta:
        model = VideoRecording
        fields = [
            'id', 'title', 'source_type', 'status',
            'processed_video_path', 'duration', 'fps',
            'suspicious_count', 'normal_count',
            'suspicious_percentage', 'created_at'
        ]


class FrameAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for incoming frame analysis requests."""
    frame = serializers.CharField(help_text='Base64 encoded frame image')
    recording_id = serializers.IntegerField(required=False, allow_null=True)
    session_id = serializers.CharField(required=False, allow_blank=True, default='')
    timestamp = serializers.DateTimeField(required=False)


class FrameAnalysisResponseSerializer(serializers.Serializer):
    """Serializer for frame analysis response."""
    detections = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of human detections with bounding boxes and classifications'
    )
    frame_with_overlay = serializers.CharField(
        help_text='Base64 encoded frame with bounding boxes and timestamp overlay'
    )
    timestamp = serializers.CharField()
    frame_number = serializers.IntegerField()


class VideoUploadSerializer(serializers.Serializer):
    """Serializer for video upload endpoint."""
    video = serializers.FileField(help_text='MP4 video file to process')
    title = serializers.CharField(max_length=255, required=False, default='Uploaded Video')


class LiveSessionSerializer(serializers.Serializer):
    """Serializer for starting/stopping a live recording session."""
    action = serializers.ChoiceField(choices=['start', 'stop'])
    session_id = serializers.CharField(required=False, allow_blank=True, default='')
    recording_id = serializers.IntegerField(required=False, allow_null=True)
