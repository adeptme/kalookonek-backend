from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Prefixing each app to ensure clean URL routing
    path('sysadmin/', include('kalookonek_backend.sysadmin.urls')),
    path('accounts/', include('kalookonek_backend.accounts.urls')),
    path('user/', include('kalookonek_backend.user.urls')),
    path('mp/', include('kalookonek_backend.mp.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
