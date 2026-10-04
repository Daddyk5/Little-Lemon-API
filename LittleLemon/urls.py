from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Send the bare root to the API instead of a 404
    path('', RedirectView.as_view(url='/api/menu-items/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include('LittleLemonAPI.urls')),
    # Djoser: /auth/users/, /auth/users/me/, /auth/token/login/, /auth/token/logout/
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    # Same Djoser endpoints also available under /api/auth/
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),
    # Login/logout links for the browsable API
    path('api-auth/', include('rest_framework.urls')),
]
