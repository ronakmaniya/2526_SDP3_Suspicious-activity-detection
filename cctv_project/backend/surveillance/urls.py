from django.urls import path

from .views import (
    ClassifyActivityView,
    DetectHumansView,
    HealthView,
    RecordingListView,
    RecordingUploadView,
    SessionResetView,
    SessionStartView,
    SessionStopView,
    StateView,
)

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('session/start/', SessionStartView.as_view(), name='session-start'),
    path('session/stop/', SessionStopView.as_view(), name='session-stop'),
    path('session/reset/', SessionResetView.as_view(), name='session-reset'),
    path('state/', StateView.as_view(), name='state'),

    path('recordings/', RecordingListView.as_view(), name='recording-list'),
    path('recordings/upload/', RecordingUploadView.as_view(), name='recording-upload'),
    
    path('detect/', DetectHumansView.as_view(), name='detect-humans'),

    path('classify/', ClassifyActivityView.as_view(), name='classify-activity'),
]
