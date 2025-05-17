"""
URL configuration for tagmi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from core import views
from core.views import GroupCreateView, GroupListView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # General Views
    path('', views.home, name='home'),

    # Group Views
    path('groups/', views.GroupListView.as_view(), name='group_list'),
    path('groups/create/', views.GroupCreateView.as_view(), name='create_group'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group_detail'),

    # Photo Upload View (your custom function-based view)
    path('photos/upload/', views.handleMultipleImagesUpload, name='upload_photo'),
    # Photo Management Views (related to Groups)
    path('groups/<int:group_pk>/photos/<int:photo_pk>/remove/', views.remove_photo_from_group_view, name='remove_photo_from_group'),

    # Tag Management Views (related to Groups)
    path('groups/<int:group_pk>/tags/add/', views.add_group_tag_view, name='add_group_tag'),
    path('groups/<int:group_pk>/tags/<int:tag_pk>/remove/', views.remove_group_tag_view, name='remove_group_tag'),

    # Photo Tag Management Views (assigning/removing tags from photos within a group context)
    path('groups/<int:group_pk>/photos/<int:photo_pk>/assign-tags/', views.assign_photo_tags_view, name='assign_photo_tags'),

    # Note: There isn't a dedicated "Photo Detail" or "Photo List" page in this setup yet.
    # Photos are primarily viewed within the context of a Group (via GroupDetailView).
    # If you need direct photo views, you would add them here.
    # Admin URL
    path('admin/', admin.site.urls),
    # Allauth URLs
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)