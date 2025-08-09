# face_recognize_live.py - ENHANCED VERSION WITH ULTRA-NATURAL VOICE SYSTEM
import cv2
import face_recognition
import numpy as np
import os
import sys
import django
import time
import threading
import pyttsx3
from queue import Queue
import pygame
import tempfile
import random
import requests
import json
from datetime import date, timedelta


# Django setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "facerecognizer.settings")
django.setup()


from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from faceapp.models import (
    KnownPerson, Attendance, TejgyanSession,
    MA_Attendance, SSP1_Attendance, SSP2_Attendance, HS1_Attendance, HS2_Attendance,
    MA_Repeaters, SSP1_Repeaters, SSP2_Repeaters, HS1_Repeaters, HS2_Repeaters
)


# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
os.environ['QT_QPA_PLATFORM'] = 'xcb'


# 🚀 ENHANCED VOICE SYSTEM CONFIGURATION
ATTENDANCE_RENEWAL_HOURS = 12
MESSAGE_DISPLAY_SECONDS = 4

# 🎤 PREMIUM TTS API CONFIGURATIONS (Add your API keys here)
ELEVENLABS_API_KEY = "your_elevenlabs_api_key_here"  # Most natural for Hindi
OPENAI_API_KEY = "your_openai_api_key_here"          # Advanced GPT-4o TTS
GOOGLE_CLOUD_CREDENTIALS = "path_to_your_google_credentials.json"  # Google WaveNet
AZURE_SPEECH_KEY = "your_azure_speech_key"           # Azure AI Speech
AZURE_REGION = "your_azure_region"

# Voice selection configuration
USE_PREMIUM_VOICES = True  # Set to True to use premium natural voices
VOICE_QUALITY = "ultra"    # Options: "basic", "premium", "ultra"


# Initialize pygame for premium audio playback
try:
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
    pygame.mixer.init()
except Exception as e:
    pass


# Enhanced voice system configuration
voice_queue = Queue()
tts_engine = None
voice_initialized = False


def initialize_voice_engine():
    """Initialize enhanced TTS engine with premium voice support"""
    global tts_engine, voice_initialized
    try:
        tts_engine = pyttsx3.init()
        voices = tts_engine.getProperty('voices')
        if voices and len(voices) > 0:
            hindi_voice = None
            english_voice = None
            for voice in voices:
                voice_name = voice.name.lower()
                if 'hindi' in voice_name or 'devanagari' in voice_name:
                    hindi_voice = voice
                    break
                elif 'english' in voice_name or 'david' in voice_name:
                    english_voice = voice
            selected_voice = hindi_voice if hindi_voice else (english_voice if english_voice else voices[0])
            tts_engine.setProperty('voice', selected_voice.id)
            tts_engine.setProperty('rate', 150)
            tts_engine.setProperty('volume', 1.0)
            voice_initialized = True
        else:
            voice_initialized = False
    except Exception as e:
        voice_initialized = False


# 🚀 PREMIUM VOICE FUNCTIONS - ULTRA-NATURAL TTS SYSTEMS


def create_elevenlabs_audio(text, gender='M'):
    """Create ultra-natural Hindi audio using ElevenLabs (Best Quality)"""
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "your_elevenlabs_api_key_here":
        return None
    
    # ElevenLabs Hindi voice IDs - these provide incredible naturalness
    voice_ids = {
        'M': "pNInz6obpgDQGcFmaJgB",  # Hindi male voice (Adam)
        'F': "EXAVITQu4vr4xnSDxMaL"   # Hindi female voice (Bella)
    }
    
    voice_id = voice_ids.get(gender, voice_ids['M'])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # Best for Hindi
        "voice_settings": {
            "stability": 0.7,           # More stable for spiritual content
            "similarity_boost": 0.8,    # Higher similarity to human speech
            "style": 0.6,              # Natural speaking style
            "use_speaker_boost": True   # Enhanced clarity
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(response.content)
                print(f"[SUCCESS] ElevenLabs audio created: {len(response.content)} bytes")
                return tmp_file.name
        else:
            print(f"[WARNING] ElevenLabs API error: {response.status_code}")
    except Exception as e:
        print(f"[WARNING] ElevenLabs error: {e}")
    
    return None


def create_google_wavenet_audio(text, gender='M'):
    """Create highly natural speech using Google Cloud WaveNet"""
    try:
        from google.cloud import texttospeech
        import os
        
        if GOOGLE_CLOUD_CREDENTIALS and os.path.exists(GOOGLE_CLOUD_CREDENTIALS):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CLOUD_CREDENTIALS
        
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Configure for Hindi with WaveNet neural voices
        voice_names = {
            'M': "hi-IN-Wavenet-B",  # Male Hindi WaveNet voice
            'F': "hi-IN-Wavenet-A"   # Female Hindi WaveNet voice
        }
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="hi-IN",
            name=voice_names.get(gender, voice_names['M']),
            ssml_gender=texttospeech.SsmlVoiceGender.MALE if gender == 'M' else texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # High-quality audio configuration
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,      # Natural speaking rate
            pitch=0.0,              # Natural pitch
            volume_gain_db=2.0,     # Slightly boosted volume
            sample_rate_hertz=24000  # High-definition quality
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tmp_file.write(response.audio_content)
            print(f"[SUCCESS] Google WaveNet audio created: {len(response.audio_content)} bytes")
            return tmp_file.name
            
    except Exception as e:
        print(f"[WARNING] Google Cloud TTS error: {e}")
    
    return None


def create_azure_neural_audio(text, gender='M'):
    """Create professional speech using Azure AI Neural voices"""
    if not AZURE_SPEECH_KEY or AZURE_SPEECH_KEY == "your_azure_speech_key":
        return None
    
    try:
        import azure.cognitiveservices.speech as speechsdk
        
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
        
        # Latest Hindi neural voices from Azure
        voice_names = {
            'M': "hi-IN-MadhurNeural",  # Male Hindi Neural voice
            'F': "hi-IN-SwaraNeural"    # Female Hindi Neural voice
        }
        
        speech_config.speech_synthesis_voice_name = voice_names.get(gender, voice_names['M'])
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3)
        
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        
        result = synthesizer.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(result.audio_data)
                print(f"[SUCCESS] Azure Neural audio created: {len(result.audio_data)} bytes")
                return tmp_file.name
        else:
            print(f"[WARNING] Azure synthesis failed: {result.reason}")
            
    except Exception as e:
        print(f"[WARNING] Azure AI Speech error: {e}")
    
    return None


def create_openai_audio(text, gender='M'):
    """Create advanced speech using OpenAI's GPT-4o TTS"""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        return None
    
    try:
        import openai
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # OpenAI's natural voices
        voice_names = {
            'M': "onyx",    # Deep, natural male voice
            'F': "nova"     # Warm, natural female voice
        }
        
        response = client.audio.speech.create(
            model="tts-1-hd",  # High-definition model
            voice=voice_names.get(gender, voice_names['M']),
            input=text,
            speed=1.0
        )
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            response.stream_to_file(tmp_file.name)
            print(f"[SUCCESS] OpenAI TTS audio created")
            return tmp_file.name
            
    except Exception as e:
        print(f"[WARNING] OpenAI TTS error: {e}")
    
    return None


def create_gtts_audio(text, gender='M'):
    """Create basic Google TTS audio file in Hindi (Fallback)"""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='hi', slow=False, tld='co.in')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts.save(tmp_file.name)
            print(f"[SUCCESS] Basic gTTS audio created")
            return tmp_file.name
    except Exception as e:
        print(f"[WARNING] gTTS error: {e}")
        return None


# 🚀 ENHANCED NATURAL AUDIO CREATION WITH INTELLIGENT FALLBACK
def create_natural_audio(text, gender='M'):
    """Enhanced natural voice system with intelligent fallback chain"""
    
    if not USE_PREMIUM_VOICES:
        return create_gtts_audio(text, gender)
    
    if VOICE_QUALITY == "ultra":
        # Try ElevenLabs first (most natural for spiritual content)
        print(f"[INFO] Attempting ElevenLabs ultra-natural voice...")
        audio_file = create_elevenlabs_audio(text, gender)
        if audio_file:
            return audio_file
        
        # Fallback to Google WaveNet (excellent Hindi)
        print(f"[INFO] Fallback to Google WaveNet...")
        audio_file = create_google_wavenet_audio(text, gender)
        if audio_file:
            return audio_file
        
        # Fallback to Azure Neural
        print(f"[INFO] Fallback to Azure Neural...")
        audio_file = create_azure_neural_audio(text, gender)
        if audio_file:
            return audio_file
    
    elif VOICE_QUALITY == "premium":
        # Try Google WaveNet first (best value)
        print(f"[INFO] Attempting Google WaveNet premium voice...")
        audio_file = create_google_wavenet_audio(text, gender)
        if audio_file:
            return audio_file
        
        # Fallback to Azure Neural
        audio_file = create_azure_neural_audio(text, gender)
        if audio_file:
            return audio_file
    
    # Final fallback to basic gTTS
    print(f"[INFO] Using basic gTTS fallback...")
    return create_gtts_audio(text, gender)


def play_audio_file(audio_file):
    """Enhanced audio playback with better error handling"""
    try:
        if pygame.mixer.get_init() and audio_file and os.path.exists(audio_file):
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to complete with timeout
            max_wait = 30  # 30 seconds timeout
            start_time = time.time()
            
            while pygame.mixer.music.get_busy():
                if time.time() - start_time > max_wait:
                    print("[WARNING] Audio playback timeout")
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.1)
            
            return True
        else:
            print(f"[WARNING] Cannot play audio file: {audio_file}")
            return False
    except Exception as e:
        print(f"[WARNING] Audio playback error: {e}")
        return False


def speak_with_pyttsx3(text, gender='M'):
    """Enhanced pyttsx3 fallback with better voice selection"""
    global tts_engine, voice_initialized
    if not voice_initialized or not tts_engine:
        initialize_voice_engine()
    
    if voice_initialized and tts_engine:
        try:
            # Adjust rate for spiritual content
            tts_engine.setProperty('rate', 140)  # Slightly slower for better understanding
            tts_engine.setProperty('volume', 0.95)
            tts_engine.say(text)
            tts_engine.runAndWait()
            return True
        except Exception as e:
            print(f"[WARNING] pyttsx3 error: {e}")
            return False
    else:
        print("[WARNING] pyttsx3 not initialized")
        return False


def voice_worker():
    """Enhanced voice worker thread with premium TTS processing"""
    print(f"[INFO] Voice worker started with {VOICE_QUALITY} quality")
    
    while True:
        try:
            voice_data = voice_queue.get(timeout=2)
            if voice_data == "STOP":
                print("[INFO] Voice worker stopping...")
                break
            
            message, gender = voice_data
            success = False
            
            # Try premium natural audio first
            if USE_PREMIUM_VOICES:
                audio_file = create_natural_audio(message, gender)
                if audio_file:
                    if play_audio_file(audio_file):
                        success = True
                    
                    # Clean up temporary file
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
            
            # Fallback to pyttsx3 if premium voices fail
            if not success:
                success = speak_with_pyttsx3(message, gender)
            
            if success:
                print(f"[SUCCESS] Voice message delivered: {message[:50]}...")
            else:
                print(f"[ERROR] Failed to deliver voice message")
            
            voice_queue.task_done()
            time.sleep(0.3)  # Shorter delay for better responsiveness
            
        except Exception as e:
            if str(e).strip() and "Empty" not in str(e):
                print(f"[WARNING] Voice worker error: {str(e)[:50]}")
            continue


def speak_ultra_clear(message, gender='M'):
    """Enhanced message queueing with priority handling"""
    try:
        # Limit message length for better performance
        if len(message) > 500:
            message = message[:500] + "..."
        
        voice_queue.put((message, gender), timeout=2)
        print(f"[QUEUE] Voice message queued: {message[:30]}...")
    except Exception as e:
        print(f"[WARNING] Voice queue error: {e}")


# Enhanced session and model functions (keeping all existing functionality)
def get_attendance_model(session_type):
    """Get the appropriate attendance model for the session type"""
    models_map = {
        'MA': MA_Attendance,
        'SSP1': SSP1_Attendance,
        'SSP2': SSP2_Attendance,
        'HS1': HS1_Attendance,
        'HS2': HS2_Attendance,
    }
    return models_map.get(session_type)


def get_repeater_model(session_type):
    """Get the appropriate repeater model for the session type"""
    models_map = {
        'MA': MA_Repeaters,
        'SSP1': SSP1_Repeaters,
        'SSP2': SSP2_Repeaters,
        'HS1': HS1_Repeaters,
        'HS2': HS2_Repeaters,
    }
    return models_map.get(session_type)


def get_session_duration(session_type):
    """Get required days for each session type"""
    durations = {
        'MA': 5,
        'SSP1': 2,
        'SSP2': 2,
        'HS1': 2,
        'HS2': 2,
        'FESTIVAL': 1
    }
    return durations.get(session_type, 1)


def get_active_session():
    """Fetch the current active session from database"""
    try:
        active_session = TejgyanSession.objects.get(is_active=True)
        return active_session
    except TejgyanSession.DoesNotExist:
        print("\n" + "="*60)
        print("WARNING: No active session found in database!")
        print("Please go to Django Admin and activate a session:")
        print("   1. Run: python manage.py runserver")
        print("   2. Visit: http://localhost:8000/admin/")
        print("   3. Go to 'Tejgyan Sessions'")
        print("   4. Create/Select a session and mark it as ACTIVE")
        print("="*60)
        return None
    except TejgyanSession.MultipleObjectsReturned:
        print("WARNING: Multiple active sessions found! Fixing...")
        active_sessions = TejgyanSession.objects.filter(is_active=True).order_by('-created_at')
        latest_session = active_sessions.first()
        active_sessions.exclude(pk=latest_session.pk).update(is_active=False)
        return latest_session


# Initialize enhanced voice system
print("[INFO] Initializing Tejgyan Foundation Enhanced Voice Recognition System...")
print(f"[INFO] Voice Quality: {VOICE_QUALITY.upper()} ({('Premium TTS APIs' if USE_PREMIUM_VOICES else 'Basic TTS')})")
print("[INFO] Separate Tables: MA(5 days) → SSP1(2 days) → SSP2(2 days) → HS1(2 days) → HS2(2 days)")
print(f"[INFO] 12-Hour Attendance Renewal System Active")

# Initialize voice engine
initialize_voice_engine()

# Start enhanced voice worker thread
try:
    voice_thread = threading.Thread(target=voice_worker, daemon=True)
    voice_thread.start()
    print("[SUCCESS] Enhanced voice worker thread started")
except Exception as e:
    print(f"[ERROR] Enhanced voice system failed: {e}")


# Get active session at startup
print("\nTejgyan Foundation Enhanced Attendance System")
print("Ultra-Natural Hindi Voice Experience")
print("Conducted by: Sirshree")
print("="*60)


ACTIVE_SESSION = get_active_session()


if ACTIVE_SESSION:
    print(f"Today's Active Session: {ACTIVE_SESSION.session_name}")
    print(f"Session Type: {ACTIVE_SESSION.get_session_type_display()}")
    print(f"Session Duration: {get_session_duration(ACTIVE_SESSION.session_type)} days")
    print(f"Session Date: {ACTIVE_SESSION.session_date}")
    print(f"Conducted by: {ACTIVE_SESSION.conducted_by}")
    print(f"Attendance Renewal: {ATTENDANCE_RENEWAL_HOURS} hours")
    print(f"Voice Quality: {VOICE_QUALITY.upper()}")
    print("="*60)
else:
    print("Cannot start face recognition without an active session!")
    print("Please activate a session in Django Admin first.")
    sys.exit(1)


# Load face encodings (keeping existing functionality)
known_face_encodings = []
known_face_metadata = []
people = KnownPerson.objects.all()


total_users = people.count()
active_users = people.filter(is_active=True).count()
inactive_users = people.filter(is_active=False).count()
blacklisted_users = people.filter(is_blacklisted=True).count()


print(f"[INFO] Loading face database:")
print(f"  Total users: {total_users}")
print(f"  Active: {active_users}")
print(f"  Inactive: {inactive_users}")
print(f"  Blacklisted: {blacklisted_users}")


loaded_encodings = 0
for person in people:
    if not person.image:
        continue
    image_path = os.path.join(settings.MEDIA_ROOT, str(person.image))
    if not os.path.isfile(image_path):
        continue
    try:
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        if encodings:
            known_face_encodings.append(encodings[0])
            known_face_metadata.append({
                "name": person.name,
                "email": person.email,
                "city": person.city,
                "shivir": person.shivir,
                "gender": person.gender,
                "is_blacklisted": person.is_blacklisted,
                "is_active": person.is_active
            })
            loaded_encodings += 1
    except Exception as e:
        print(f"[WARNING] Error loading {person.name}: {str(e)}")


print(f"[INFO] Successfully loaded {loaded_encodings} face encodings")
print(f"[INFO] Enhanced voice system ready with {VOICE_QUALITY} quality")


if not known_face_encodings:
    print("[ERROR] No face encodings loaded. Check user images.")
    sys.exit(1)


# 🎤 ENHANCED HINDI VOICE MESSAGES WITH ULTRA-NATURAL DELIVERY
def get_session_continuation_message(name, gender, session_type, day_number):
    """Generate ultra-natural Hindi message for session continuation"""
    session_names = {
        'MA': 'एम ए शिविर',
        'SSP1': 'एस एस पी वन शिविर',
        'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन',
        'HS2': 'हायर शिविर टू',
        'FESTIVAL': 'त्योहार सत्संग'
    }
    session_hindi = session_names.get(session_type, 'शिविर')
    return f"हैप्पी थॉट्स {name}, {session_hindi} के दिन {day_number} में आपकी उपस्थिति दर्ज की गई है। धन्यवाद।"


def get_session_completion_message(name, gender, session_type):
    """Generate ultra-natural Hindi message for session completion"""
    session_names = {
        'MA': 'एम ए शिविर',
        'SSP1': 'एस एस पी वन शिविर',
        'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन',
        'HS2': 'हायर शिविर टू',
        'FESTIVAL': 'त्योहार सत्संग'
    }
    session_hindi = session_names.get(session_type, 'शिविर')
    return f"बधाई हो {name}! आपने {session_hindi} सफलतापूर्वक पूरा कर लिया है। आपकी आध्यात्मिक यात्रा में यह एक महत्वपूर्ण उपलब्धि है।"


def get_blacklist_message(name, gender):
    """Generate natural Hindi blacklist notification"""
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में प्रतिबंधित सूची में हैं। कृपया एडमिन से संपर्क करें। धन्यवाद।"


def get_inactive_message(name, gender):
    """Generate natural Hindi inactive user message"""
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय हैं। कृपया एडमिन से संपर्क करके सक्रियता प्राप्त करें। धन्यवाद।"


def get_inactive_and_blacklisted_message(name, gender):
    """Generate natural Hindi message for dual status users"""
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय और प्रतिबंधित सूची दोनों में हैं। कृपया तुरंत एडमिन से संपर्क करें। धन्यवाद।"


def get_new_user_guidance_message(name, gender):
    """Generate warm Hindi welcome for new users"""
    return f"हैप्पी थॉट्स {name}, तेजज्ञान फाउंडेशन में आपका हार्दिक स्वागत है। कृपया पहले एम ए शिविर से अपनी आध्यात्मिक यात्रा शुरू करें। धन्यवाद।"


def get_not_eligible_message(name, gender, current_session, user_level):
    """Generate natural Hindi eligibility message"""
    session_names = {
        'MA': 'एम ए शिविर',
        'SSP1': 'एस एस पी वन शिविर',
        'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन',
        'HS2': 'हायर शिविर टू',
        'FESTIVAL': 'त्योहार सत्संग'
    }
    current_hindi = session_names.get(current_session, 'शिविर')
    return f"हैप्पी थॉट्स {name}, आप {current_hindi} के लिए योग्य नहीं हैं। कृपया पहले पिछला स्तर पूरा करें। धन्यवाद।"


def get_attendance_marked_message(name, gender):
    """Generate warm Hindi successful attendance message"""
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति सफलतापूर्वक दर्ज हो गई है। आपकी आध्यात्मिक यात्रा में यह एक सुंदर कदम है। धन्यवाद।"


def get_already_marked_message(name, gender):
    """Generate gentle Hindi already marked message"""
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति पहले ही दर्ज हो चुकी है। आपका समय और ध्यान देने के लिए धन्यवाद।"


def get_12_hour_wait_message(name, gender, hours_remaining):
    """Generate patient Hindi 12-hour waiting message"""
    if hours_remaining < 1:
        minutes = int(hours_remaining * 60)
        if minutes <= 1:
            return f"हैप्पी थॉट्स {name}, कृपया थोड़ी देर प्रतीक्षा करें और फिर उपस्थिति दर्ज करें। धन्यवाद।"
        else:
            return f"हैप्पी थॉट्स {name}, कृपया {minutes} मिनट बाद उपस्थिति दर्ज करें। धैर्य रखें। धन्यवाद।"
    elif hours_remaining < 2:
        return f"हैप्पी थॉट्स {name}, कृपया एक घंटे बाद उपस्थिति दर्ज करें। आपका धैर्य सराहनीय है। धन्यवाद।"
    else:
        hours = int(hours_remaining)
        return f"हैप्पी थॉट्स {name}, कृपया {hours} घंटे बाद उपस्थिति दर्ज करें। आप अपने समय का सदुपयोग करें। धन्यवाद।"


def get_repeater_welcome_message(name, gender, days_gap):
    """Generate warm Hindi repeater welcome with spiritual context"""
    return f"हैप्पी थॉट्स {name}, {days_gap} दिन बाद आपका पुनरागमन अत्यंत स्वागत है। आपकी निरंतर साधना प्रेरणादायक है। आपकी उपस्थिति दर्ज की गई है। धन्यवाद।"


def get_repeater_already_marked_message(name, gender):
    """Generate gentle Hindi repeater already marked message"""
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति पहले से ही दर्ज है। आपकी निरंतरता सराहनीय है। धन्यवाद।"


# Keep all existing attendance logic functions (check_12_hour_renewal, check_if_repeat_attendance, etc.)
def check_12_hour_renewal(person, active_session):
    """Check if user can mark attendance based on 12-hour renewal period"""
    renewal_threshold = timezone.now() - timedelta(hours=ATTENDANCE_RENEWAL_HOURS)
    
    last_attendance = Attendance.objects.filter(
        person=person,
        session=active_session,
        timestamp__gte=renewal_threshold
    ).order_by('-timestamp').first()
    
    if not last_attendance:
        return True, "Can mark attendance"
    
    now = timezone.now()
    time_diff = now - last_attendance.timestamp
    hours_passed = time_diff.total_seconds() / 3600
    
    if hours_passed >= ATTENDANCE_RENEWAL_HOURS:
        return True, f"Can mark attendance (last marked {hours_passed:.1f} hours ago)"
    else:
        hours_remaining = ATTENDANCE_RENEWAL_HOURS - hours_passed
        return False, hours_remaining


def check_session_12_hour_renewal(person, session_type, today):
    """Check 12-hour renewal for session-specific tables"""
    AttendanceModel = get_attendance_model(session_type)
    
    if AttendanceModel:
        renewal_threshold = timezone.now() - timedelta(hours=ATTENDANCE_RENEWAL_HOURS)
        recent_session_attendance = AttendanceModel.objects.filter(
            person=person,
            created_at__gte=renewal_threshold
        ).exists()
        
        if recent_session_attendance:
            last_session_attendance = AttendanceModel.objects.filter(
                person=person
            ).order_by('-created_at').first()
            
            if last_session_attendance:
                time_diff = timezone.now() - last_session_attendance.created_at
                hours_passed = time_diff.total_seconds() / 3600
                hours_remaining = ATTENDANCE_RENEWAL_HOURS - hours_passed
                return False, hours_remaining
        
        return True, 0
    
    return True, 0


def check_if_repeat_attendance(person, session_type, today):
    """Check if this is repeat attendance using separate tables"""
    if session_type == 'FESTIVAL':
        return False, None
    
    AttendanceModel = get_attendance_model(session_type)
    if not AttendanceModel:
        return False, None
    
    completed_attendance = AttendanceModel.objects.filter(
        person=person,
        is_completed=True
    ).order_by('-attendance_date').first()
    
    if completed_attendance:
        last_completion_date = completed_attendance.attendance_date
        
        RepeaterModel = get_repeater_model(session_type)
        if RepeaterModel:
            last_repeat = RepeaterModel.objects.filter(person=person).order_by('-repeat_attendance_date').first()
            if last_repeat:
                last_completion_date = last_repeat.repeat_attendance_date
        
        days_gap = (today - last_completion_date).days
        
        return True, {
            'last_completion_date': last_completion_date,
            'days_gap': days_gap
        }
    
    return False, None


def get_user_eligible_sessions(person, user_shivir_level):
    """Get eligible sessions for user based on their shivir level"""
    progression_order = ['MA', 'SSP1', 'SSP2', 'HS1', 'HS2']
    eligible_sessions = []
    
    if not user_shivir_level:
        eligible_sessions = ['MA']
    else:
        try:
            current_level_index = progression_order.index(user_shivir_level)
            for i in range(current_level_index + 1):
                eligible_sessions.append(progression_order[i])
            if current_level_index + 1 < len(progression_order):
                next_level = progression_order[current_level_index + 1]
                eligible_sessions.append(next_level)
        except ValueError:
            eligible_sessions = ['MA']
    
    if 'FESTIVAL' not in eligible_sessions:
        eligible_sessions.append('FESTIVAL')
    
    return eligible_sessions


# 🚀 MAIN ATTENDANCE FUNCTION WITH ENHANCED NATURAL VOICE
def mark_attendance_with_ultra_voice(email, name, gender):
    """Enhanced attendance marking with ultra-natural voice delivery"""
    try:
        matched_person = KnownPerson.objects.get(email=email)
    except KnownPerson.DoesNotExist:
        return None

    # Handle user status with enhanced voice messages
    if not matched_person.is_active and matched_person.is_blacklisted:
        status = "User is Inactive & Blacklisted!"
        voice_message = get_inactive_and_blacklisted_message(name, gender)
        speak_ultra_clear(voice_message, gender)
        return status

    elif not matched_person.is_active:
        status = "User is Inactive!"
        voice_message = get_inactive_message(name, gender)
        speak_ultra_clear(voice_message, gender)
        return status

    elif matched_person.is_blacklisted:
        status = "User is Blacklisted!"
        voice_message = get_blacklist_message(name, gender)
        speak_ultra_clear(voice_message, gender)
        return status

    # Main attendance logic with enhanced voice experience
    else:
        today = date.today()
        current_session_type = ACTIVE_SESSION.session_type
        
        user_shivir_level = matched_person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(matched_person, user_shivir_level)
        
        if current_session_type not in eligible_sessions:
            if not user_shivir_level:
                status = "New User - Must Start with MA!"
                voice_message = get_new_user_guidance_message(name, gender)
                speak_ultra_clear(voice_message, gender)
                return status
            else:
                status = f"Not Eligible for {current_session_type}!"
                voice_message = get_not_eligible_message(name, gender, current_session_type, user_shivir_level)
                speak_ultra_clear(voice_message, gender)
                return status
        
        # 12-hour renewal check with enhanced messages
        can_mark_general, renewal_info = check_12_hour_renewal(matched_person, ACTIVE_SESSION)
        
        if not can_mark_general:
            hours_remaining = renewal_info
            
            if hours_remaining > 1:
                status = f"Please wait {hours_remaining:.1f} hours before next attendance"
            else:
                minutes_remaining = int(hours_remaining * 60)
                status = f"Please wait {minutes_remaining} minutes before next attendance"
            
            voice_message = get_12_hour_wait_message(name, gender, hours_remaining)
            speak_ultra_clear(voice_message, gender)
            return status
        
        # Handle repeat attendance with warm messages
        is_repeat, repeat_info = check_if_repeat_attendance(matched_person, current_session_type, today)
        
        if is_repeat:
            days_gap = repeat_info['days_gap']
            last_completion_date = repeat_info['last_completion_date']
            
            can_mark_repeat, repeat_renewal_info = check_12_hour_renewal(matched_person, ACTIVE_SESSION)
            
            if not can_mark_repeat:
                hours_remaining = repeat_renewal_info
                status = f"Repeat attendance - please wait {hours_remaining:.1f} hours"
                voice_message = get_12_hour_wait_message(name, gender, hours_remaining)
                speak_ultra_clear(voice_message, gender)
                return status
            
            RepeaterModel = get_repeater_model(current_session_type)
            
            if RepeaterModel:
                renewal_threshold = timezone.now() - timedelta(hours=ATTENDANCE_RENEWAL_HOURS)
                existing_repeat_recent = RepeaterModel.objects.filter(
                    person=matched_person,
                    created_at__gte=renewal_threshold
                ).exists()
                
                if not existing_repeat_recent:
                    repeat_count = RepeaterModel.objects.filter(person=matched_person).count() + 1
                    
                    try:
                        RepeaterModel.objects.create(
                            person=matched_person,
                            previous_attendance_date=last_completion_date,
                            days_gap=days_gap,
                            repeat_count=repeat_count
                        )
                        print(f"[SUCCESS] Created repeater record for {name}")
                    except IntegrityError as e:
                        print(f"[WARNING] Repeater record already exists for {name}: {e}")
            
            try:
                Attendance.objects.create(
                    person=matched_person,
                    session=ACTIVE_SESSION
                )
                print(f"[SUCCESS] Created general attendance for repeater {name}")
                
                # Enhanced voice messages for repeaters
                voice_message_1 = get_repeater_welcome_message(name, gender, days_gap)
                speak_ultra_clear(voice_message_1, gender)
                
                time.sleep(3)  # Longer pause for better experience
                
                voice_message_2 = get_repeater_already_marked_message(name, gender)
                speak_ultra_clear(voice_message_2, gender)
                
                status = f"Repeat Attendance - Welcome Back After {days_gap} Days!"
                return status
                
            except IntegrityError as e:
                print(f"[WARNING] General attendance already exists for repeater {name}: {e}")
                voice_message = get_already_marked_message(name, gender)
                speak_ultra_clear(voice_message, gender)
                status = f"Already marked for {ACTIVE_SESSION.get_session_type_display()}!"
                return status
        
        # Handle normal attendance with enhanced voice experience
        if current_session_type == 'FESTIVAL':
            try:
                Attendance.objects.create(
                    person=matched_person,
                    session=ACTIVE_SESSION
                )
                print(f"[SUCCESS] Created festival attendance for {name}")
                
                voice_message = get_attendance_marked_message(name, gender)
                speak_ultra_clear(voice_message, gender)
                return f"Festival Attendance Marked!"
                
            except IntegrityError as e:
                print(f"[WARNING] Festival attendance already exists for {name}: {e}")
                voice_message = get_already_marked_message(name, gender)
                speak_ultra_clear(voice_message, gender)
                return f"Already marked for {ACTIVE_SESSION.get_session_type_display()}!"
        
        else:
            # Multi-day session handling with enhanced voice
            AttendanceModel = get_attendance_model(current_session_type)
            
            if AttendanceModel:
                can_mark_session, session_renewal_info = check_session_12_hour_renewal(matched_person, current_session_type, today)
                
                if not can_mark_session:
                    hours_remaining = session_renewal_info
                    
                    if hours_remaining > 1:
                        status = f"Session attendance - please wait {hours_remaining:.1f} hours"
                    else:
                        minutes_remaining = int(hours_remaining * 60)
                        status = f"Session attendance - please wait {minutes_remaining} minutes"
                    
                    voice_message = get_12_hour_wait_message(name, gender, hours_remaining)
                    speak_ultra_clear(voice_message, gender)
                    return status
                
                total_days_attended = AttendanceModel.objects.filter(person=matched_person).count()
                session_duration = get_session_duration(current_session_type)
                day_number = total_days_attended + 1
                
                is_completing = (day_number >= session_duration)
                
                try:
                    AttendanceModel.objects.create(
                        person=matched_person,
                        day_number=day_number,
                        session_reference=ACTIVE_SESSION,
                        is_completed=is_completing
                    )
                    print(f"[SUCCESS] Created {current_session_type} attendance for {name} - Day {day_number}")
                except IntegrityError as e:
                    print(f"[WARNING] {current_session_type} attendance already exists for {name}: {e}")
                    voice_message = get_already_marked_message(name, gender)
                    speak_ultra_clear(voice_message, gender)
                    return f"Already marked for {ACTIVE_SESSION.get_session_type_display()}!"
                
                try:
                    Attendance.objects.create(
                        person=matched_person,
                        session=ACTIVE_SESSION
                    )
                    print(f"[SUCCESS] Created general attendance for {name}")
                except IntegrityError as e:
                    print(f"[WARNING] General attendance already exists for {name}: {e}")
                
                if is_completing and current_session_type != 'FESTIVAL':
                    print(f"[INFO] Session completed! Updating shivir field...")
                    success = matched_person.update_shivir_field_on_completion(current_session_type)
                    if success:
                        print(f"[SUCCESS] Shivir field updated to {current_session_type}!")
                    else:
                        print(f"[INFO] Shivir field not updated (see debug output)")
                
                # Enhanced voice messages for session progress
                if is_completing:
                    voice_message = get_session_completion_message(name, gender, current_session_type)
                    speak_ultra_clear(voice_message, gender)
                    status = f"🎉 Session Completed - {ACTIVE_SESSION.get_session_type_display()}!"
                else:
                    voice_message_1 = get_session_continuation_message(name, gender, current_session_type, day_number)
                    speak_ultra_clear(voice_message_1, gender)
                    
                    time.sleep(3)  # Pause for better experience
                    
                    voice_message_2 = get_already_marked_message(name, gender)
                    speak_ultra_clear(voice_message_2, gender)
                    
                    status = f"Day {day_number}/{session_duration} - {ACTIVE_SESSION.get_session_type_display()}"
                
                return status
        
        return "Attendance processed"


# Keep all existing display and UI functions
def get_user_color(metadata):
    """Get color based on user status combination and eligibility"""
    if metadata['name'] == "Unknown":
        return (0, 0, 255)
    
    is_inactive = not metadata.get('is_active', True)
    is_blacklisted = metadata.get('is_blacklisted', False)
    
    try:
        person = KnownPerson.objects.get(email=metadata['email'])
        user_level = person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(person, user_level)
        is_eligible = ACTIVE_SESSION.session_type in eligible_sessions
    except:
        is_eligible = True
    
    if is_inactive and is_blacklisted:
        return (0, 0, 139)
    elif is_blacklisted:
        return (0, 0, 255)
    elif is_inactive:
        return (0, 165, 255)
    elif not is_eligible:
        return (0, 140, 255)
    else:
        return (255, 0, 255) if metadata['gender'] == 'F' else (0, 255, 0)


def get_status_display(metadata):
    if metadata['name'] == "Unknown":
        return "Unknown Person"
    
    is_inactive = not metadata.get('is_active', True)
    is_blacklisted = metadata.get('is_blacklisted', False)
    
    try:
        person = KnownPerson.objects.get(email=metadata['email'])
        user_level = person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(person, user_level)
        is_eligible = ACTIVE_SESSION.session_type in eligible_sessions
    except:
        is_eligible = True
    
    if is_inactive and is_blacklisted:
        return "INACTIVE & BLACKLISTED"
    elif is_blacklisted:
        return "BLACKLISTED"
    elif is_inactive:
        return "INACTIVE"
    elif not is_eligible:
        return "NOT ELIGIBLE"
    else:
        return "Active & Eligible"


def get_gender_display(gender):
    if gender == 'F':
        return 'Female'
    elif gender == 'M':
        return 'Male'
    else:
        return ''


# Cache management
message_cache = {}

# Video capture setup
video_capture = cv2.VideoCapture(0)
if not video_capture.isOpened():
    print("[ERROR] Could not open webcam.")
    sys.exit(1)

video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print(f"[INFO] Tejgyan Face Recognition started for: {ACTIVE_SESSION.session_name}")
print(f"[INFO] Ultra-Natural Voice Experience with {VOICE_QUALITY.upper()} quality")
print("[INFO] Press 'q' to quit.")

try:
    while True:
        ret, frame = video_capture.read()
        if not ret:
            time.sleep(0.2)
            continue

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        now = time.time()

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matched_metadata = {
                "name": "Unknown", 
                "email": "", 
                "city": "", 
                "shivir": "", 
                "gender": "", 
                "is_blacklisted": False,
                "is_active": True
            }
            status_message = ""

            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                best_distance = face_distances[best_match_index]
            else:
                best_distance = 1.0

            threshold = 0.5

            if best_distance < threshold:
                matched_metadata = known_face_metadata[best_match_index]
                email = matched_metadata['email']
                name = matched_metadata['name']
                gender = matched_metadata['gender']

                # Enhanced attendance marking with natural voice
                if email not in message_cache or now > message_cache[email]['visible_until']:
                    status_message = mark_attendance_with_ultra_voice(email, name, gender)
                    message_cache[email] = {
                        'message': status_message,
                        'visible_until': now + MESSAGE_DISPLAY_SECONDS
                    }
                else:
                    status_message = message_cache[email]['message']

            # Scale coordinates back
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Enhanced UI with voice quality indicator
            color = get_user_color(matched_metadata)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            info_lines = [
                f"Name: {matched_metadata['name']}",
                f"Gender: {get_gender_display(matched_metadata['gender'])}",
                f"Email: {matched_metadata['email']}",
                f"City: {matched_metadata['city']}",
                f"Shivir: {matched_metadata['shivir']}",
                f"Status: {get_status_display(matched_metadata)}"
            ]
            
            if ACTIVE_SESSION and matched_metadata['name'] != "Unknown":
                info_lines.append(f"Session: {ACTIVE_SESSION.session_type}")
                info_lines.append(f"Voice: {VOICE_QUALITY.upper()}")

            y_text = bottom + 20
            for line in info_lines:
                cv2.putText(frame, line, (left, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_text += 20

            # Enhanced status message display
            if status_message:
                message_width = max(200, len(status_message) * 8)
                
                if "wait" in status_message.lower() and ("hour" in status_message or "minute" in status_message):
                    bg_color = (0, 100, 150)
                    border_color = (0, 150, 255)
                    message_color = (255, 255, 255)
                elif "Inactive & Blacklisted" in status_message:
                    bg_color = (0, 0, 80)
                    border_color = (0, 0, 139)
                    message_color = (255, 255, 255)
                elif "Blacklisted" in status_message:
                    bg_color = (0, 0, 100)
                    border_color = (0, 0, 255)
                    message_color = (255, 255, 255)
                elif "Inactive" in status_message:
                    bg_color = (0, 80, 100)
                    border_color = (0, 165, 255)
                    message_color = (255, 255, 255)
                elif "Not Eligible" in status_message or "New User" in status_message:
                    bg_color = (0, 100, 140)
                    border_color = (0, 140, 255)
                    message_color = (255, 255, 255)
                elif "Repeat Attendance" in status_message:
                    bg_color = (100, 50, 0)
                    border_color = (150, 100, 0)
                    message_color = (255, 255, 255)
                elif "Session Completed" in status_message:
                    bg_color = (0, 150, 0)
                    border_color = (0, 255, 0)
                    message_color = (255, 255, 0)
                elif matched_metadata['gender'] == 'F':
                    bg_color = (100, 0, 100)
                    border_color = (255, 0, 255)
                    message_color = (255, 255, 0) if "Day" in status_message else (0, 255, 255)
                else:
                    bg_color = (0, 100, 0)
                    border_color = (0, 255, 0)
                    message_color = (255, 255, 0) if "Day" in status_message else (0, 255, 255)
                
                cv2.rectangle(frame, (left, y_text + 5), (left + message_width, y_text + 35), bg_color, -1)
                cv2.rectangle(frame, (left, y_text + 5), (left + message_width, y_text + 35), border_color, 2)
                cv2.putText(frame, status_message, (left + 5, y_text + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, message_color, 2)

        # Clean up expired messages
        expired_emails = [email for email, data in message_cache.items() if now > data['visible_until']]
        for email in expired_emails:
            del message_cache[email]

        cv2.imshow(f"Tejgyan Foundation - Enhanced Voice System ({VOICE_QUALITY.upper()})", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[INFO] Quitting...")
            break

except KeyboardInterrupt:
    print("[INFO] Interrupted by user.")

finally:
    voice_queue.put("STOP")
    try:
        voice_thread.join(timeout=5)
    except:
        pass
    
    if pygame.mixer.get_init():
        pygame.mixer.quit()
    
    video_capture.release()
    cv2.destroyAllWindows()
    print("[INFO] Enhanced Tejgyan Voice System shutdown complete.")
