# faceapp/voice_helper.py - UPDATED for ElevenLabs v2.8+ with YOUR CREDENTIALS
from elevenlabs.client import ElevenLabs
from elevenlabs import play, save
import pygame
import tempfile
import os
import logging

# 🔥 YOUR ELEVENLABS CREDENTIALS INTEGRATED
ELEVENLABS_API_KEY = 'sk_11de27c9cee94fe617e3f768b6124bc857dea2a18f1c8af4'  # YOUR API KEY
YOUR_VOICE_ID = 'H6QPv2pQZDcGqLwDTIJQ'  # YOUR VOICE ID (Kanishka)
SINGLE_VOICE = 'Kanishka'  # YOUR VOICE NAME

# Set up logging
logger = logging.getLogger('elevenlabs')

# Setup ElevenLabs client with YOUR credentials
try:
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    print("✅ ElevenLabs client initialized successfully with YOUR credentials")
    print(f"🔑 Using YOUR API Key: {ELEVENLABS_API_KEY[:20]}...")
    print(f"🎤 Using YOUR Voice ID: {YOUR_VOICE_ID}")
except Exception as e:
    print(f"❌ ElevenLabs initialization error: {e}")
    client = None

# Setup pygame for audio playback
try:
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.8)
    print("✅ Pygame audio system initialized")
except Exception as e:
    print(f"❌ Pygame initialization error: {e}")

def speak(message):
    """
    🔥 Updated function for ElevenLabs v2.8+ API with YOUR credentials
    Usage: speak("हैप्पी थॉट्स! आपकी उपस्थिति दर्ज हो गई है।")
    """
    if not client:
        print("❌ ElevenLabs client not available - using fallback")
        speak_fallback(message)
        return
    
    try:
        print(f"🎤 Speaking with YOUR voice: {message}")
        print(f"🔑 Using YOUR API Key: {ELEVENLABS_API_KEY[:20]}...")
        print(f"🎵 Using YOUR Voice ID: {YOUR_VOICE_ID}")
        
        # Generate voice audio with YOUR credentials using new API
        audio = client.text_to_speech.convert(
            text=message,
            voice_id=YOUR_VOICE_ID,  # 🔥 YOUR VOICE ID
            model_id="eleven_multilingual_v2",  # Best for Hindi
            output_format="mp3_44100_128"
        )
        
        # Save to temporary file and play
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            # Write audio data to file
            for chunk in audio:
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        # Play the audio using pygame
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        # Wait for voice to finish
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        print(f"✅ Successfully spoke with YOUR voice: {message}")
        
    except Exception as e:
        print(f"❌ YOUR ElevenLabs voice error: {e}")
        print("🔄 Falling back to system TTS")
        speak_fallback(message)

def speak_hindi(hindi_message):
    """
    🔥 Dedicated function for Hindi messages using YOUR ElevenLabs voice
    Usage: speak_hindi("हैप्पी थॉट्स! एम ए शिविर में आपकी उपस्थिति दर्ज हो गई है।")
    """
    if not client:
        print("❌ ElevenLabs client not available - using fallback")
        speak_fallback(hindi_message)
        return
    
    try:
        print(f"🎤 Speaking Hindi with YOUR voice: {hindi_message}")
        
        # Generate Hindi voice audio with optimized settings
        audio = client.text_to_speech.convert(
            text=hindi_message,
            voice_id=YOUR_VOICE_ID,  # 🔥 YOUR VOICE ID
            model_id="eleven_multilingual_v2",  # Best for Hindi
            output_format="mp3_44100_128",
            voice_settings={
                "stability": 0.85,
                "similarity_boost": 0.90,
                "style": 1.0,
                "use_speaker_boost": True
            }
        )
        
        # Save to temporary file and play
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            # Write audio data to file
            for chunk in audio:
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        # Play the audio
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        # Wait for voice to finish
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        # Clean up
        os.unlink(tmp_path)
        print(f"✅ Successfully spoke Hindi with YOUR voice: {hindi_message}")
        
    except Exception as e:
        print(f"❌ YOUR Hindi voice error: {e}")
        print("🔄 Falling back to system TTS")
        speak_fallback(hindi_message)

def get_voice_id(voice_name):
    """
    🔥 Updated to return YOUR voice ID when requested
    """
    # If requesting your specific voice, return your voice ID
    if voice_name in ['Kanishka', SINGLE_VOICE, 'YOUR_VOICE']:
        return YOUR_VOICE_ID  # 🔥 YOUR VOICE ID
    
    # Common voice IDs for quick reference (in case you want to test others)
    voice_map = {
        'Rachel': 'N2lVS1w4EtoT3dr4eOWO',
        'Drew': '29vD33N1CtxCmqQRPOHJ', 
        'Clyde': '2EiwWnXFnvU5JabPnv8n',
        'Paul': 'pNInz6obpgDQGcFmaJgB',
        'Domi': 'AZnzlk1XvdvUeBnXmlld',
        'Dave': 'CYw3kZ02Hs0563khs1Fj',
        'Fin': 'D38z5RcWu1voky8WS1ja',
        'Sarah': 'EXAVITQu4vr4xnSDxMaL',
        'Antoni': 'ErXwobaYiN019PkySvjV',
        'Thomas': 'GBv7mTt0atIp3Br8iCZE',
        'Charlie': 'IKne3meq5aSn9XLyUdCD',
        'George': 'JBFqnCBsd6RMkjVDRZzb',
        'Emily': 'LcfcDJNUP1GQjkzn1xUU',
        'Elli': 'MF3mGyEYCl7XYWbV9V6O',
        'Callum': 'N2lVS1w4EtoT3dr4eOWO',
        'Patrick': 'ODq5zmih8GrVes37Dizd',
        'Harry': 'SOYHLrjzK2X1ezoPC6cr',
        'Liam': 'TX3LPaxmHKxFdv7VOQHJ',
        'Dorothy': 'ThT5KcBeYPX3keUQqHPh',
        'Josh': 'TxGEqnHWrfWFTfGW9XjX',
        'Arnold': 'VR6AewLTigWG4xSOukaG',
        'Charlotte': 'XB0fDUnXU5powFXDhCwa',
        'Alice': 'Xb7hH8MSUJpSbSDYk0k2',
        'Matilda': 'XrExE9yKIg1WjnnlVkGX',
        'James': 'ZQe5CqHNLWdVhgEeSBaN',
        'Joseph': 'Zlb1dXrM653N07WRdFW3',
        'Jeremy': 'bVMeCyTHy58xNoL34h3p',
        'Michael': 'flq6f7yk4E4fJM5XTYuZ',
        'Ethan': 'g5CIjZEefAph4nQFvHAz',
        'Gigi': 'jBpfuIE2acCO8z3wKNLl',
        'Freya': 'jsCqWAovK2LkecY7zXl4',
        'Brian': 'nPczCjzI2devNBz1zQrb',
        'Grace': 'oWAxZDx7w5VEj9dCyTzz',
        'Daniel': 'onwK4e9ZLuTAKqWW03F9',
        'Lily': 'pFZP5JQG7iQjIQuC4Bku',
        'Serena': 'pMsXgVXv3BLzUgSXRplE',
        'Adam': 'pNInz6obpgDQGcFmaJgB',
        'Nicole': 'piTKgcLEGmPE4e6mEKli',
        'Jessie': 't0jbNlBVZ17f02VDIeMI',
        'Ryan': 'wViXBPUzp2ZZixB1xQuM',
        'Sam': 'yoZ06aMxZJJ28mfd3POQ',
        'Glinda': 'z9fAnlkpzviPz146aGWa',
        'Giovanni': 'zcAOhNBS3c14rBihAFp1',
        'Mimi': 'zrHiDhphv9ZnVXBqCLjz',
        'Kanishka': YOUR_VOICE_ID,  # 🔥 YOUR VOICE
    }
    
    # Return the voice ID or default to YOUR voice
    return voice_map.get(voice_name, YOUR_VOICE_ID)  # 🔥 Default to YOUR voice

def speak_fallback(message):
    """
    Fallback TTS using system capabilities when YOUR ElevenLabs fails
    """
    try:
        print(f"🔄 Using fallback TTS for: {message}")
        
        # Try using system TTS as fallback
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(message)
            engine.runAndWait()
            print("✅ Fallback TTS completed")
        except ImportError:
            print("📢 TTS Fallback (pyttsx3 not available):", message)
            
    except Exception as e:
        print(f"❌ Fallback TTS also failed: {e}")
        print(f"📝 Message: {message}")

def test_your_voice():
    """
    🔥 Test YOUR specific ElevenLabs voice
    """
    try:
        print("🧪 Testing YOUR ElevenLabs voice...")
        print(f"🔑 API Key: {ELEVENLABS_API_KEY[:20]}...")
        print(f"🎤 Voice ID: {YOUR_VOICE_ID}")
        
        # Test with Hindi message
        hindi_test = "हैप्पी थॉट्स! यह आपकी आवाज़ का परीक्षण है।"
        speak_hindi(hindi_test)
        
        # Test with English message
        english_test = "Hello! This is a test of your ElevenLabs voice."
        speak(english_test)
        
        return True
    except Exception as e:
        print(f"❌ YOUR voice test failed: {e}")
        return False

def list_available_voices():
    """
    🔥 List all voices available in YOUR ElevenLabs account
    """
    try:
        if not client:
            print("❌ ElevenLabs client not available")
            return []
        
        print("🎤 Fetching voices from YOUR ElevenLabs account...")
        voices = client.voices.get_all()
        
        print("📋 Available voices in YOUR account:")
        for voice in voices.voices:
            print(f"  - {voice.name} (ID: {voice.voice_id})")
            if voice.voice_id == YOUR_VOICE_ID:
                print(f"    🔥 ↑ THIS IS YOUR CONFIGURED VOICE!")
        
        return voices.voices
    except Exception as e:
        print(f"❌ Error fetching voices: {e}")
        return []

def test_voice_system():
    """
    🔥 Test YOUR complete voice system
    """
    try:
        print("🧪 Testing YOUR complete voice system...")
        
        # Test 1: Basic functionality
        print("Test 1: Basic English")
        speak("Voice system test successful with your credentials!")
        
        # Test 2: Hindi functionality  
        print("Test 2: Hindi voice")
        speak_hindi("आपकी आवाज़ सिस्टम सफलतापूर्वक काम कर रहा है!")
        
        # Test 3: List voices
        print("Test 3: Account voices")
        list_available_voices()
        
        return True
    except Exception as e:
        print(f"❌ YOUR voice system test failed: {e}")
        return False

# 🔥 CREATE VOICE_SETTINGS FILE FOR COMPATIBILITY
def create_voice_settings_file():
    """
    Create voice_settings.py file with YOUR credentials
    """
    settings_content = f'''# voice_settings.py - YOUR ELEVENLABS CREDENTIALS
# Generated automatically with YOUR API credentials

# 🔥 YOUR ELEVENLABS API CONFIGURATION
ELEVENLABS_API_KEY = '{ELEVENLABS_API_KEY}'
SINGLE_VOICE = '{SINGLE_VOICE}'
YOUR_VOICE_ID = '{YOUR_VOICE_ID}'

# Voice configuration settings
VOICE_SETTINGS = {{
    'stability': 0.85,
    'similarity_boost': 0.90,
    'style': 1.0,
    'use_speaker_boost': True
}}

print("✅ Voice settings loaded with YOUR credentials")
print(f"🔑 API Key: {{ELEVENLABS_API_KEY[:20]}}...")
print(f"🎤 Voice: {{SINGLE_VOICE}} ({{YOUR_VOICE_ID}})")
'''
    
    try:
        with open('voice_settings.py', 'w', encoding='utf-8') as f:
            f.write(settings_content)
        print("✅ Created voice_settings.py with YOUR credentials")
    except Exception as e:
        print(f"❌ Error creating voice_settings.py: {e}")

# Initialize and test on import
if __name__ == "__main__":
    print("🚀 Initializing YOUR ElevenLabs voice system...")
    create_voice_settings_file()  # Create settings file
    test_voice_system()  # Test the system
else:
    print("📦 YOUR ElevenLabs voice helper loaded successfully")
    print(f"🔑 Using API Key: {ELEVENLABS_API_KEY[:20]}...")
    print(f"🎤 Using Voice: {SINGLE_VOICE} ({YOUR_VOICE_ID})")
