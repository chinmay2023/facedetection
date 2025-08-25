"""facerecognizer URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
# facerecognizer/urls.py - CORRECTED VERSION (No Import Errors)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from faceapp.api_views import (
    mark_attendance, blacklist_person, unblacklist_person, blacklist_status
    # Removed non-existent functions to prevent ImportError
)

urlpatterns = [
    # ✅ EXISTING - Admin Interface (Your sophisticated admin system)
    path('admin/', admin.site.urls),
    
    # 🆕 NEW - Face Recognition Attendance Interface
    path('attendance/', include('faceapp.urls')),
    
    # ✅ EXISTING - Your current API endpoints (Working!)
    path('api/mark_attendance/', mark_attendance, name='mark_attendance'),
    path('api/blacklist/', blacklist_person, name='blacklist_person'),
    path('api/unblacklist/', unblacklist_person, name='unblacklist_person'),
    path('api/blacklist_status/<str:email>/', blacklist_status, name='blacklist_status'),
    
    # 🔄 REMOVED - These functions don't exist yet in api_views.py
    # path('api/activate/', activate_person, name='activate_person'),
    # path('api/deactivate/', deactivate_person, name='deactivate_person'), 
    # path('api/activation_status/<str:email>/', activation_status, name='activation_status'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    