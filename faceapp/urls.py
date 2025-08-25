# faceapp/urls.py
from django.urls import path
from . import views

app_name = 'faceapp'
urlpatterns = [
    path('', views.attendance_interface, name='attendance'),
    path('api/recognize_face/', views.recognize_face_api, name='recognize_face'),
]
