# faceapp/voice_settings.py - YOUR ELEVENLABS CREDENTIALS
# Auto-generated with YOUR API credentials

# 🔥 YOUR ELEVENLABS API CONFIGURATION
ELEVENLABS_API_KEY = 'sk_11de27c9cee94fe617e3f768b6124bc857dea2a18f1c8af4'  # YOUR API KEY
SINGLE_VOICE = 'Kanishka'  # YOUR VOICE NAME  
YOUR_VOICE_ID = 'H6QPv2pQZDcGqLwDTIJQ'  # YOUR VOICE ID

# Voice configuration settings
VOICE_SETTINGS = {
    'stability': 0.85,
    'similarity_boost': 0.90,
    'style': 1.0,
    'use_speaker_boost': True
}

print("Voice settings loaded with YOUR credentials")
print(f"API Key: {ELEVENLABS_API_KEY[:20]}...")
print(f"Voice: {SINGLE_VOICE} ({YOUR_VOICE_ID})")
