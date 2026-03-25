# ticketsite/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # include booking app urls under root so /, /create-order/, /verify-payment/, /generate-ticket/ work
    path("", include("booking.urls")),
]

# serve media in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
