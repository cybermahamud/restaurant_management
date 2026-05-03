# restaurant_management/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('accounts:login' if not request.user.is_authenticated else 'common:dashboard'), name='root'),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.common.urls')),
    path('restaurant/', include('apps.restaurant.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('orders/', include('apps.orders.urls')),
    path('reports/', include('apps.reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)