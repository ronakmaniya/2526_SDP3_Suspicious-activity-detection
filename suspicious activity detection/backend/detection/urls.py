"""
URL routing for the detection API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'events', views.DetectionEventViewSet, basename='events')
router.register(r'recordings', views.VideoRecordingViewSet, basename='recordings')

urlpatterns = [
    # AI Processing endpoints
    path('analyze-frame/', views.FrameAnalysisView.as_view(), name='analyze-frame'),
    path('live-session/', views.LiveSessionView.as_view(), name='live-session'),
    path('upload-video/', views.VideoUploadView.as_view(), name='upload-video'),

    # System endpoints
    path('health/', views.health_check, name='health-check'),
    path('stats/', views.system_stats, name='system-stats'),

    # Router URLs (events, recordings)
    path('', include(router.urls)),
]
