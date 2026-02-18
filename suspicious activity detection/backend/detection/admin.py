from django.contrib import admin
from .models import DetectionEvent, VideoRecording


@admin.register(DetectionEvent)
class DetectionEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'label', 'confidence', 'duration', 'created_at')
    list_filter = ('label', 'timestamp')
    search_fields = ('label',)
    ordering = ('-timestamp',)
    readonly_fields = ('created_at',)


@admin.register(VideoRecording)
class VideoRecordingAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'source_type', 'status', 'duration', 'created_at')
    list_filter = ('source_type', 'status')
    search_fields = ('title',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
