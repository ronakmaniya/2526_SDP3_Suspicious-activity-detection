import os
import time
from pathlib import Path

from django.conf import settings
from django.utils.text import get_valid_filename
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import STATE, get_state, reset_state, start_session, stop_session, tick_simulation


class HealthView(APIView):
    def get(self, request):
        return Response({'status': 'ok'})


class SessionStartView(APIView):
    def post(self, request):
        start_session()
        return Response({'running': True})


class SessionStopView(APIView):
    def post(self, request):
        stop_session()
        return Response({'running': False})


class SessionResetView(APIView):
    def post(self, request):
        reset_state()
        return Response({'running': False})


class StateView(APIView):
    """Return the latest detection/alert/stat state.

    For now this also advances the simulation each time it's polled.
    """

    def get(self, request):
        if STATE.running:
            tick_simulation()
            activity_status = STATE.detections[-1]['status'] if STATE.detections else 'normal'
        else:
            activity_status = 'idle'

        return Response(get_state(activity_status))


class RecordingUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Upload a recorded video file.

        Expects multipart form-data with:
        - file: video/webm
        - startedAt (optional): ISO string
        - endedAt (optional): ISO string
        """

        uploaded = request.FILES.get('file')
        if uploaded is None:
            return Response({'error': 'Missing file field'}, status=400)

        recordings_dir = Path(settings.MEDIA_ROOT)
        recordings_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime('%Y%m%d_%H%M%S')
        original_name = get_valid_filename(getattr(uploaded, 'name', 'recording.webm'))
        base_name = f"recording_{ts}_{original_name}"
        out_path = recordings_dir / base_name

        # Avoid overwriting
        if out_path.exists():
            out_path = recordings_dir / f"recording_{ts}_{int(time.time() * 1000)}_{original_name}"

        with open(out_path, 'wb') as f:
            for chunk in uploaded.chunks():
                f.write(chunk)

        rel_path = out_path.relative_to(settings.MEDIA_ROOT).as_posix()
        url = f"{settings.MEDIA_URL}{out_path.name}"

        return Response(
            {
                'saved': True,
                'filename': out_path.name,
                'path': rel_path,
                'url': url,
                'startedAt': request.data.get('startedAt'),
                'endedAt': request.data.get('endedAt'),
                'size': os.path.getsize(out_path),
            }
        )


class RecordingListView(APIView):
    def get(self, request):
        recordings_dir = Path(settings.MEDIA_ROOT)
        recordings_dir.mkdir(parents=True, exist_ok=True)

        items = []
        for p in sorted(recordings_dir.glob('*.webm'), key=lambda x: x.stat().st_mtime, reverse=True):
            rel_path = p.relative_to(settings.MEDIA_ROOT).as_posix()
            items.append(
                {
                    'filename': p.name,
                    'url': f"{settings.MEDIA_URL}{p.name}",
                    'size': p.stat().st_size,
                    'modifiedAt': int(p.stat().st_mtime),
                }
            )

        return Response({'recordings': items})
