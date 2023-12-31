"""
URL configuration for sarakste project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from sarakste_app.views import *
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView


urlpatterns = [
    path('admin/', admin.site.urls),
]

from django.views.generic import RedirectView

urlpatterns += [
    path('', RedirectView.as_view(url='sarakste/', permanent=True)),
    path('login', login_view, name='login_view'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  # Add logout view
    path('lasit/', display_snippets, name='display_snippets'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('segments/', generate_segment_links, name='generate_segment_links'),
    path('temas/', display_summaries, name='display_summaries'),
    path('meklet/', search, name='search'),
    path('delete_snippet/<int:snippet_id>/', delete_snippet, name='delete_snippet'),
    path('atzimeti/', list_marked_snippets, name='list_marked_snippets'),
    path('mileti/', list_loved_snippets, name='list_loved_snippets'),

]

# Use static() to add URL mapping to serve static files during development (only)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
