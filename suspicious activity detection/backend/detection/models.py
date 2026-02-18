"""
Database models for the Suspicious Activity Detection System.
Stores detection events, video recordings, and processing metadata.
"""
from django.db import models
from django.utils import timezone


class DetectionEvent(models.Model):
    """
    Stores individual detection events logged by the AI pipeline.
    Each event represents a detected human with activity classification.
    """
    LABEL_CHOICES = [
        ('normal', 'Normal'),
        ('suspicious', 'Suspicious'),
    ]

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    label = models.CharField(max_length=20, choices=LABEL_CHOICES, db_index=True)
    confidence = models.FloatField(help_text='Confidence score between 0 and 1')
    video_path = models.CharField(max_length=500, blank=True, null=True)
    duration = models.FloatField(
        default=0.0,
        help_text='Duration of suspicious activity in seconds'
    )
    bounding_box = models.JSONField(
        default=dict,
        help_text='Bounding box coordinates {x1, y1, x2, y2}'
    )
    frame_number = models.IntegerField(default=0)
    recording = models.ForeignKey(
        'VideoRecording',
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Detection Event'
        verbose_name_plural = 'Detection Events'
        indexes = [
            models.Index(fields=['label', 'timestamp']),
            models.Index(fields=['confidence']),
        ]

    def __str__(self):
        return f"[{self.label.upper()}] {self.confidence:.2f} at {self.timestamp}"


class VideoRecording(models.Model):
    """
    Stores metadata about video recordings (live and uploaded).
    """
    SOURCE_CHOICES = [
        ('live', 'Live Recording'),
        ('upload', 'Uploaded Video'),
    ]

    STATUS_CHOICES = [
        ('recording', 'Recording'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=255, default='Untitled Recording')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='live')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='recording')
    original_video_path = models.CharField(max_length=500, blank=True, null=True)
    processed_video_path = models.CharField(max_length=500, blank=True, null=True)
    duration = models.FloatField(default=0.0, help_text='Duration in seconds')
    fps = models.FloatField(default=24.0)
    resolution_width = models.IntegerField(default=640)
    resolution_height = models.IntegerField(default=480)
    total_frames = models.IntegerField(default=0)
    suspicious_count = models.IntegerField(default=0)
    normal_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Video Recording'
        verbose_name_plural = 'Video Recordings'

    def __str__(self):
        return f"{self.title} ({self.source_type}) - {self.status}"

    @property
    def suspicious_percentage(self):
        total = self.suspicious_count + self.normal_count
        if total == 0:
            return 0
        return round((self.suspicious_count / total) * 100, 2)
