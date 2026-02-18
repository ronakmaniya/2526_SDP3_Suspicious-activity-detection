from django.apps import AppConfig


class DetectionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'detection'
    verbose_name = 'Suspicious Activity Detection'

    def ready(self):
        """Initialize AI models when the app is ready."""
        pass
