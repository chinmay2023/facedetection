#faceapp/voice_helper.py
# Ultra simple voice helper - ONE voice for ALL text
from elevenlabs import generate, set_api_key
import pygame
import tempfile
import os
from .voice_settings import ELEVENLABS_API_KEY, SINGLE_VOICE

# Setup voice system
set_api_key(ELEVENLABS_API_KEY)
pygame.mixer.init()
pygame.mixer.music.set_volume(0.8)  # Set volume level

def speak(message):
    """
    Super simple function - ONE voice speaks ANY text
    Usage: speak("Any message here!")
    """
    try:
        print(f"🎤 Speaking: {message}")
        
        # Generate voice audio with same voice always
        audio = generate(
            text=message,
            voice=SINGLE_VOICE,          # Same voice always
            model="eleven_flash_v2_5"    # Fast voice (75ms latency)
        )
        
        # Play the audio
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_file.write(audio)
            tmp_path = tmp_file.name
        
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        # Wait for voice to finish
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        # Clean up
        os.unlink(tmp_path)
        print(f"✅ Successfully spoke: {message}")
        
    except Exception as e:
        print(f"❌ Voice error: {e}")

# That's it! Just one simple function for everything
