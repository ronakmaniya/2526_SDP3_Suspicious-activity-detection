from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


def root_redirect(_request):
    return HttpResponseRedirect('/api/health/')

urlpatterns = [
    path('', root_redirect),
    path('admin/', admin.site.urls),
    path('api/', include('surveillance.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
