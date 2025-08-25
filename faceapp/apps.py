# faceapp/apps.py
from django.apps import AppConfig

class FaceappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'faceapp'
    
    def ready(self):
        # 🔥 THIS IS THE CRITICAL LINE - Import signals to register them
        import faceapp.signals
        print("📡 FaceApp signals registered successfully!")
