# face_recognize_live.py - ENHANCED WITH SMART VOICE MESSAGES FOR COMPLETED SESSIONS + FIXED REPEATER DUPLICATES
import os
import sys
from contextlib import contextmanager

@contextmanager
def suppress_all_output():
    """Completely suppress stdout and stderr for silent operations"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

# ✅ ENHANCED: Comprehensive camera optimization with output suppression
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
os.environ["OPENCV_VIDEOIO_PRIORITY_V4L2"] = "1"
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
os.environ['SDL_VIDEODRIVER'] = "dummy"

# Suppress pygame import messages
with suppress_all_output():
    import pygame.mixer

import cv2
import face_recognition
import numpy as np
import django
import time
import threading
import pyttsx3
from queue import Queue
import tempfile
import requests
import json
from datetime import date, timedelta
import subprocess
import platform

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

# ================================
# 🎤 SIMPLE SINGLE FEMALE VOICE CONFIGURATION
# ================================

# ✅ ElevenLabs API Configuration
ELEVENLABS_API_KEY = "sk_28cca7b5ed320c52750c33b0d8568ca1d29c4a748c8dcba4"  # Your API key
USE_ELEVENLABS = True

# SINGLE VOICE SELECTION - CHANGE ONLY THIS LINE TO SWITCH VOICES
SELECTED_VOICE_ID = "H6QPv2pQZDcGqLwDTIJQ"  #Kanishka - Clear, professional (DEFAULT)

print(f"[INFO] Selected Female Voice: {SELECTED_VOICE_ID}")

# ================================
# END OF VOICE CONFIGURATION
# ================================

# Enhanced voice configuration
ATTENDANCE_RENEWAL_HOURS = 0.0
MESSAGE_DISPLAY_SECONDS = 10

# Initialize pygame with suppressed output
with suppress_all_output():
    try:
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
    except Exception as e:
        pass

# Enhanced voice system configuration
voice_queue = Queue()
tts_engine = None
voice_initialized = False

# ✅ UPDATED ELEVENLABS VOICE INTEGRATION - SINGLE FEMALE VOICE ONLY
def create_elevenlabs_audio(text, gender='F'):
    """Create audio using ElevenLabs API - SINGLE FEMALE VOICE"""
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "sk-your-elevenlabs-api-key-here":
        return None
    
    # Always use your selected female voice
    voice_id = SELECTED_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # Supports Hindi
        "voice_settings": {
            "stability": 0.85,
            "similarity_boost": 0.90,
            "style": 1.0,
            "use_speaker_boost": True
        }
    }
    
    with suppress_all_output():
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                    tmp_file.write(response.content)
                    return tmp_file.name
        except Exception as e:
            print(f"ElevenLabs error: {e}")
    return None

def play_audio_file(audio_file):
    """Play audio file using pygame"""
    with suppress_all_output():
        try:
            if pygame.mixer.get_init() and audio_file and os.path.exists(audio_file):
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                max_wait = 30
                start_time = time.time()
                
                while pygame.mixer.music.get_busy():
                    if time.time() - start_time > max_wait:
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.1)
                return True
            return False
        except:
            return False

def initialize_pyttsx3_engine():
    """Initialize pyttsx3 engine as fallback"""
    global tts_engine, voice_initialized
    with suppress_all_output():
        try:
            tts_engine = pyttsx3.init()
            voices = tts_engine.getProperty('voices')
            if voices and len(voices) > 0:
                # Try to find female voice first
                female_voice = None
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        female_voice = voice
                        break
                
                if female_voice:
                    tts_engine.setProperty('voice', female_voice.id)
                else:
                    # Use first available voice
                    tts_engine.setProperty('voice', voices[0].id)
                
                tts_engine.setProperty('rate', 140)
                tts_engine.setProperty('volume', 0.9)
                voice_initialized = True
            else:
                voice_initialized = False
        except Exception as e:
            voice_initialized = False

def speak_with_pyttsx3(text, gender='F'):
    """Fallback speech using pyttsx3 - Always female voice"""
    global tts_engine, voice_initialized
    if not voice_initialized:
        initialize_pyttsx3_engine()
    
    if voice_initialized and tts_engine:
        with suppress_all_output():
            try:
                tts_engine.say(text)
                tts_engine.runAndWait()
                return True
            except:
                return False
    return False

# ✅ ENHANCED VOICE WORKER - ALWAYS FEMALE VOICE
def voice_worker():
    """Enhanced voice worker with female-only ElevenLabs integration"""
    while True:
        try:
            voice_data = voice_queue.get(timeout=2)
            if voice_data == "STOP":
                break
            
            message, gender = voice_data  # gender is ignored, always female
            success = False
            
            # Try ElevenLabs with selected female voice first
            if USE_ELEVENLABS:
                audio_file = create_elevenlabs_audio(message, 'F')  # Always female
                if audio_file:
                    if play_audio_file(audio_file):
                        success = True
                    # Clean up temp file
                    with suppress_all_output():
                        try:
                            os.unlink(audio_file)
                        except:
                            pass
            
            # Fallback to pyttsx3 with female voice if ElevenLabs fails
            if not success:
                success = speak_with_pyttsx3(message, 'F')  # Always female
            
            voice_queue.task_done()
            time.sleep(0.2)
        except:
            continue

def speak_ultra_human(message, gender='F'):
    """Queue voice message for speaking - FEMALE ONLY VERSION"""
    with suppress_all_output():
        try:
            if len(message) > 500:
                message = message[:500] + "..."
            # Always use female voice regardless of gender parameter
            voice_queue.put((message, 'F'), timeout=2)
        except:
            pass

# ✅ ENHANCED CAMERA DETECTION FUNCTIONS
def check_camera_permissions():
    """Check if user has camera permissions"""
    with suppress_all_output():
        try:
            if platform.system() == "Linux":
                result = subprocess.run(['groups'], capture_output=True, text=True)
                return 'video' in result.stdout
            return True
        except Exception as e:
            return True

def check_video_devices():
    """Check for available video devices on Linux"""
    with suppress_all_output():
        try:
            if platform.system() == "Linux":
                result = subprocess.run(['ls', '/dev/'], capture_output=True, text=True)
                video_devices = [line for line in result.stdout.split('\n') if line.startswith('video')]
                return len(video_devices) > 0
            return True
        except:
            return True

def test_camera_with_backend(index, backend, backend_name):
    """Test a specific camera index with a specific backend"""
    with suppress_all_output():
        try:
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    return cap
                else:
                    cap.release()
            return None
        except Exception as e:
            return None

def initialize_camera_with_fallbacks():
    """Enhanced camera initialization with comprehensive fallbacks"""
    
    # Check permissions and video devices silently
    check_camera_permissions()
    check_video_devices()
    
    # Define backends to try
    if platform.system() == "Windows":
        backends = [(cv2.CAP_DSHOW, "DirectShow"), (cv2.CAP_MSMF, "Media Foundation"), (cv2.CAP_ANY, "Any")]
    elif platform.system() == "Linux":
        backends = [(cv2.CAP_V4L2, "V4L2"), (cv2.CAP_ANY, "Any")]
    else:
        backends = [(cv2.CAP_ANY, "Any")]
    
    # Try each backend with multiple camera indices
    for backend, backend_name in backends:
        for camera_idx in range(10):  # Test indices 0-9
            cap = test_camera_with_backend(camera_idx, backend, backend_name)
            if cap:
                # Configure optimal settings
                with suppress_all_output():
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                return cap, {'index': camera_idx, 'backend': backend_name}
    
    # If all else fails, try without specifying backend
    for camera_idx in range(5):
        with suppress_all_output():
            try:
                cap = cv2.VideoCapture(camera_idx)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        return cap, {'index': camera_idx, 'backend': 'Default'}
                    cap.release()
            except:
                continue
    
    return None, None

# Session and model functions
def get_attendance_model(session_type):
    models_map = {
        'MA': MA_Attendance, 'SSP1': SSP1_Attendance, 'SSP2': SSP2_Attendance,
        'HS1': HS1_Attendance, 'HS2': HS2_Attendance,
    }
    return models_map.get(session_type)

def get_repeater_model(session_type):
    models_map = {
        'MA': MA_Repeaters, 'SSP1': SSP1_Repeaters, 'SSP2': SSP2_Repeaters,
        'HS1': HS1_Repeaters, 'HS2': HS2_Repeaters,
    }
    return models_map.get(session_type)

def get_session_duration(session_type):
    durations = {'MA': 5, 'SSP1': 2, 'SSP2': 2, 'HS1': 2, 'HS2': 2, 'FESTIVAL': 1}
    return durations.get(session_type, 1)

def get_active_session():
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

# ✅ SYSTEM INITIALIZATION
print("[INFO] Initializing Tejgyan Foundation Face Recognition System...")
print(f"[INFO] Voice System: {'ElevenLabs AI (Female Voice)' if USE_ELEVENLABS else 'pyttsx3 Fallback (Female Voice)'}")

# Initialize voice engine
initialize_pyttsx3_engine()

# Start enhanced voice worker thread
try:
    voice_thread = threading.Thread(target=voice_worker, daemon=True)
    voice_thread.start()
    if USE_ELEVENLABS:
        print("[SUCCESS] ElevenLabs AI female voice system started")
    else:
        print("[SUCCESS] pyttsx3 female voice system started")
except Exception as e:
    print(f"[ERROR] Voice system failed: {e}")

# Get active session
print("\nTejgyan Foundation Attendance System")
print("Enhanced ElevenLabs Female Voice Experience")
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
    print("="*60)
else:
    print("Cannot start face recognition without an active session!")
    print("Please activate a session in Django Admin first.")
    sys.exit(1)

# Load face encodings
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

if not known_face_encodings:
    print("[ERROR] No face encodings loaded. Check user images.")
    sys.exit(1)

# ✅ ENHANCED Hindi voice messages with SMART COMPLETION LOGIC
def get_session_continuation_message(name, gender, session_type, day_number):
    session_names = {
        'MA': 'एम ए शिविर', 'SSP1': 'एस एस पी वन शिविर', 'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन', 'HS2': 'हायर शिविर टू', 'FESTIVAL': 'त्योहार सत्संग'
    }
    session_hindi = session_names.get(session_type, 'शिविर')
    return f"हैप्पी थॉट्स {name}, {session_hindi} के दिन {day_number} में आपकी उपस्थिति दर्ज की गई है, धन्यवाद।"

def get_session_completion_message(name, gender, session_type):
    session_names = {
        'MA': 'एम ए शिविर', 'SSP1': 'एस एस पी वन शिविर', 'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन', 'HS2': 'हायर शिविर टू', 'FESTIVAL': 'त्योहार सत्संग'
    }
    session_hindi = session_names.get(session_type, 'शिविर')
    return f"हैप्पी थॉट्स, बधाई हो {name}! आपने {session_hindi} सफलतापूर्वक पूरा कर लिया है। आपकी आध्यात्मिक यात्रा में यह एक महत्वपूर्ण उपलब्धि है, धन्यवाद।"

def get_session_already_completed_message(name, gender, session_type):
    """Smart message for users who have already completed their entire session"""
    session_names = {
        'MA': 'एम ए शिविर', 'SSP1': 'एस एस पी वन शिविर', 'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन', 'HS2': 'हायर शिविर टू', 'FESTIVAL': 'त्योहार सत्संग'
    }
    session_hindi = session_names.get(session_type, 'शिविर')
    return f"हैप्पी थॉट्स {name}, आपका आज का {session_hindi} पूरा हो गया है। कृपया अगले शिविर के लिए भविष्य में आएं, धन्यवाद।"

def get_blacklist_message(name, gender):
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में प्रतिबंधित सूची में हैं। कृपया एडमिन से संपर्क करें, धन्यवाद।"

def get_inactive_message(name, gender):
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय हैं। कृपया एडमिन से संपर्क करके सक्रियता प्राप्त करें, धन्यवाद।"

def get_inactive_and_blacklisted_message(name, gender):
    return f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय और प्रतिबंधित सूची दोनों में हैं। कृपया तुरंत एडमिन से संपर्क करें, धन्यवाद।"

def get_new_user_guidance_message(name, gender):
    return f"हैप्पी थॉट्स {name}, तेजज्ञान फाउंडेशन में आपका हार्दिक स्वागत है। कृपया पहले एम ए शिविर से अपनी आध्यात्मिक यात्रा शुरू करें, धन्यवाद।"

def get_not_eligible_message(name, gender, current_session, user_level):
    session_names = {
        'MA': 'एम ए शिविर', 'SSP1': 'एस एस पी वन शिविर', 'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन', 'HS2': 'हायर शिविर टू', 'FESTIVAL': 'त्योहार सत्संग'
    }
    current_hindi = session_names.get(current_session, 'शिविर')
    return f"हैप्पी थॉट्स {name}, आप {current_hindi} के लिए योग्य नहीं हैं, कृपया पहले पिछला स्तर पूरा करें, धन्यवाद।"

def get_attendance_marked_message(name, gender):
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति सफलतापूर्वक दर्ज हो गई है, आपकी आध्यात्मिक यात्रा में यह एक सुंदर कदम है, धन्यवाद।"

def get_already_marked_message(name, gender):
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति पहले ही दर्ज हो चुकी है। आपका समय और ध्यान देने के लिए धन्यवाद।"

def get_12_hour_wait_message(name, gender, hours_remaining):
    if hours_remaining < 1:
        minutes = int(hours_remaining * 60)
        if minutes <= 1:
            return f"हैप्पी थॉट्स {name}, कृपया थोड़ी देर प्रतीक्षा करें और फिर उपस्थिति दर्ज करें, धन्यवाद।"
        else:
            return f"हैप्पी थॉट्स {name}, कृपया {minutes} मिनट बाद उपस्थिति दर्ज करें, धैर्य रखें, धन्यवाद।"
    elif hours_remaining < 2:
        return f"हैप्पी थॉट्स {name}, कृपया एक घंटे बाद उपस्थिति दर्ज करें, आपका धैर्य सराहनीय है, धन्यवाद।"
    else:
        hours = int(hours_remaining)
        return f"हैप्पी थॉट्स {name}, कृपया {hours} घंटे बाद उपस्थिति दर्ज करें। आप अपने समय का सदुपयोग करें, धन्यवाद।"

def get_repeater_welcome_message(name, gender, days_gap):
    return f"हैप्पी थॉट्स {name}, {days_gap} दिन बाद आपका पुनरागमन अत्यंत स्वागत है। आपकी निरंतर साधना प्रेरणादायक है, आपकी उपस्थिति दर्ज की गई है, धन्यवाद।"

def get_repeater_already_marked_message(name, gender):
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति पहले से ही दर्ज है, आपकी निरंतरता सराहनीय है, धन्यवाद।"

# ✅ MINIMAL FIX 1: Safe repeater creation function - NO MORE DUPLICATES!
def create_repeater_record_safely(RepeaterModel, person, last_completion_date, days_gap):
    """Create repeater record ONLY if it doesn't exist for today"""
    today = date.today()
    
    # Check if repeater record already exists for TODAY
    existing_repeater = RepeaterModel.objects.filter(
        person=person,
        repeat_attendance_date=today
    ).first()
    
    if existing_repeater:
        return existing_repeater, False  # Already exists
    
    # Create new record only if doesn't exist
    repeat_count = RepeaterModel.objects.filter(person=person).count() + 1
    
    try:
        repeater = RepeaterModel.objects.create(
            person=person,
            previous_attendance_date=last_completion_date,
            days_gap=days_gap,
            repeat_count=repeat_count
        )
        return repeater, True  # Successfully created
    except IntegrityError:
        # Handle race condition
        existing = RepeaterModel.objects.filter(
            person=person,
            repeat_attendance_date=today
        ).first()
        return existing, False  # Already exists

# Attendance logic functions
def check_12_hour_renewal(person, active_session):
    renewal_threshold = timezone.now() - timedelta(hours=ATTENDANCE_RENEWAL_HOURS)
    last_attendance = Attendance.objects.filter(
        person=person, session=active_session, timestamp__gte=renewal_threshold
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
    AttendanceModel = get_attendance_model(session_type)
    if AttendanceModel:
        renewal_threshold = timezone.now() - timedelta(hours=ATTENDANCE_RENEWAL_HOURS)
        recent_session_attendance = AttendanceModel.objects.filter(
            person=person, created_at__gte=renewal_threshold
        ).exists()
        
        if recent_session_attendance:
            last_session_attendance = AttendanceModel.objects.filter(person=person).order_by('-created_at').first()
            if last_session_attendance:
                time_diff = timezone.now() - last_session_attendance.created_at
                hours_passed = time_diff.total_seconds() / 3600
                hours_remaining = ATTENDANCE_RENEWAL_HOURS - hours_passed
                return False, hours_remaining
        return True, 0
    return True, 0

def check_if_repeat_attendance(person, session_type, today):
    if session_type == 'FESTIVAL':
        return False, None
    
    AttendanceModel = get_attendance_model(session_type)
    if not AttendanceModel:
        return False, None
    
    completed_attendance = AttendanceModel.objects.filter(person=person, is_completed=True).order_by('-attendance_date').first()
    
    if completed_attendance:
        last_completion_date = completed_attendance.attendance_date
        RepeaterModel = get_repeater_model(session_type)
        if RepeaterModel:
            last_repeat = RepeaterModel.objects.filter(person=person).order_by('-repeat_attendance_date').first()
            if last_repeat:
                last_completion_date = last_repeat.repeat_attendance_date
        
        days_gap = (today - last_completion_date).days
        return True, {'last_completion_date': last_completion_date, 'days_gap': days_gap}
    
    return False, None

def get_user_eligible_sessions(person, user_shivir_level):
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

def mark_attendance_with_ultra_voice(email, name, gender):
    try:
        matched_person = KnownPerson.objects.get(email=email)
    except KnownPerson.DoesNotExist:
        return None

    if not matched_person.is_active and matched_person.is_blacklisted:
        status = "User is Inactive & Blacklisted!"
        voice_message = get_inactive_and_blacklisted_message(name, 'F')
        speak_ultra_human(voice_message, 'F')
        return status

    elif not matched_person.is_active:
        status = "User is Inactive!"
        voice_message = get_inactive_message(name, 'F')
        speak_ultra_human(voice_message, 'F')
        return status

    elif matched_person.is_blacklisted:
        status = "User is Blacklisted!"
        voice_message = get_blacklist_message(name, 'F')
        speak_ultra_human(voice_message, 'F')
        return status

    else:
        today = date.today()
        current_session_type = ACTIVE_SESSION.session_type
        
        user_shivir_level = matched_person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(matched_person, user_shivir_level)
        
        if current_session_type not in eligible_sessions:
            if not user_shivir_level:
                status = "New User - Must Start with MA!"
                voice_message = get_new_user_guidance_message(name, 'F')
                speak_ultra_human(voice_message, 'F')
                return status
            else:
                status = f"Not Eligible for {current_session_type}!"
                voice_message = get_not_eligible_message(name, 'F', current_session_type, user_shivir_level)
                speak_ultra_human(voice_message, 'F')
                return status
        
        can_mark_general, renewal_info = check_12_hour_renewal(matched_person, ACTIVE_SESSION)
        
        if not can_mark_general:
            hours_remaining = renewal_info
            if hours_remaining > 1:
                status = f"Please wait {hours_remaining:.1f} hours before next attendance"
            else:
                minutes_remaining = int(hours_remaining * 60)
                status = f"Please wait {minutes_remaining} minutes before next attendance"
            
            voice_message = get_12_hour_wait_message(name, 'F', hours_remaining)
            speak_ultra_human(voice_message, 'F')
            return status
        
        is_repeat, repeat_info = check_if_repeat_attendance(matched_person, current_session_type, today)
        
        if is_repeat:
            days_gap = repeat_info['days_gap']
            last_completion_date = repeat_info['last_completion_date']
            
            can_mark_repeat, repeat_renewal_info = check_12_hour_renewal(matched_person, ACTIVE_SESSION)
            
            if not can_mark_repeat:
                hours_remaining = repeat_renewal_info
                status = f"Repeat attendance - please wait {hours_remaining:.1f} hours"
                voice_message = get_12_hour_wait_message(name, 'F', hours_remaining)
                speak_ultra_human(voice_message, 'F')
                return status
            
            # ✅ MINIMAL FIX 2: Use safe repeater creation function
            RepeaterModel = get_repeater_model(current_session_type)
            if RepeaterModel:
                repeater, repeater_created = create_repeater_record_safely(
                    RepeaterModel, matched_person, last_completion_date, days_gap
                )
                
                if not repeater_created:
                    # Repeater record already exists for today
                    voice_message = get_repeater_already_marked_message(name, 'F')
                    speak_ultra_human(voice_message, 'F')
                    return f"Repeat attendance already marked for today!"
            
            # Create general attendance record
            try:
                Attendance.objects.create(person=matched_person, session=ACTIVE_SESSION)
                
                voice_message_1 = get_repeater_welcome_message(name, 'F', days_gap)
                speak_ultra_human(voice_message_1, 'F')
                time.sleep(3)
                voice_message_2 = get_repeater_already_marked_message(name, 'F')
                speak_ultra_human(voice_message_2, 'F')
                
                status = f"Repeat Attendance - Welcome Back After {days_gap} Days!"
                return status
                
            except IntegrityError:
                voice_message = get_already_marked_message(name, 'F')
                speak_ultra_human(voice_message, 'F')
                status = f"Already marked for {ACTIVE_SESSION.get_session_type_display()}!"
                return status
        
        if current_session_type == 'FESTIVAL':
            try:
                Attendance.objects.create(person=matched_person, session=ACTIVE_SESSION)
                voice_message = get_attendance_marked_message(name, 'F')
                speak_ultra_human(voice_message, 'F')
                return f"Festival Attendance Marked!"
            except IntegrityError:
                voice_message = get_already_marked_message(name, 'F')
                speak_ultra_human(voice_message, 'F')
                return f"Already marked for {ACTIVE_SESSION.get_session_type_display()}!"
        
        else:
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
                    
                    voice_message = get_12_hour_wait_message(name, 'F', hours_remaining)
                    speak_ultra_human(voice_message, 'F')
                    return status
                
                existing_attendance = AttendanceModel.objects.filter(
                    person=matched_person,
                    session_reference=ACTIVE_SESSION
                ).first()
                
                session_duration = get_session_duration(current_session_type)
                
                if existing_attendance:
                    if existing_attendance.is_completed:
                        voice_message = get_session_already_completed_message(name, 'F', current_session_type)
                        speak_ultra_human(voice_message, 'F')
                        return f"✅ Session Already Completed - Come for Next Session"
                        
                    elif existing_attendance.day_number < session_duration:
                        existing_attendance.day_number += 1
                        existing_attendance.attendance_date = today
                        
                        if existing_attendance.day_number >= session_duration:
                            existing_attendance.is_completed = True
                        
                        existing_attendance.save()
                        
                        try:
                            Attendance.objects.create(person=matched_person, session=ACTIVE_SESSION)
                        except IntegrityError:
                            pass
                        
                        if existing_attendance.is_completed:
                            success = matched_person.update_shivir_field_on_completion(current_session_type)
                            voice_message = get_session_completion_message(name, 'F', current_session_type)
                            speak_ultra_human(voice_message, 'F')
                            status = f"🎉 Session Completed - {ACTIVE_SESSION.get_session_type_display()}!"
                        else:
                            voice_message_1 = get_session_continuation_message(name, 'F', current_session_type, existing_attendance.day_number)
                            speak_ultra_human(voice_message_1, 'F')
                            time.sleep(3)
                            voice_message_2 = get_already_marked_message(name, 'F')
                            speak_ultra_human(voice_message_2, 'F')
                            status = f"Day {existing_attendance.day_number}/{session_duration} - {ACTIVE_SESSION.get_session_type_display()}"
                        
                        return status
                    
                    else:
                        voice_message = get_already_marked_message(name, 'F')
                        speak_ultra_human(voice_message, 'F')
                        return f"Already marked for today!"
                
                else:
                    try:
                        AttendanceModel.objects.create(
                            person=matched_person,
                            day_number=1,
                            session_reference=ACTIVE_SESSION,
                            is_completed=(session_duration == 1)
                        )
                    except IntegrityError:
                        voice_message = get_already_marked_message(name, 'F')
                        speak_ultra_human(voice_message, 'F')
                        return f"Already marked for {ACTIVE_SESSION.get_session_type_display()}!"
                    
                    try:
                        Attendance.objects.create(person=matched_person, session=ACTIVE_SESSION)
                    except IntegrityError:
                        pass
                    
                    if session_duration == 1:
                        success = matched_person.update_shivir_field_on_completion(current_session_type)
                        voice_message = get_session_completion_message(name, 'F', current_session_type)
                        speak_ultra_human(voice_message, 'F')
                        status = f"🎉 Session Completed - {ACTIVE_SESSION.get_session_type_display()}!"
                    else:
                        voice_message_1 = get_session_continuation_message(name, 'F', current_session_type, 1)
                        speak_ultra_human(voice_message_1, 'F')
                        time.sleep(3)
                        voice_message_2 = get_already_marked_message(name, 'F')
                        speak_ultra_human(voice_message_2, 'F')
                        status = f"Day 1/{session_duration} - {ACTIVE_SESSION.get_session_type_display()}"
                    
                    return status
        
        return "Attendance processed"

# Display and UI functions
def get_user_color(metadata):
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

# Camera initialization
print("[INFO] Initializing enhanced female voice camera system...")
start_time = time.time()

video_capture, camera_info = initialize_camera_with_fallbacks()

if video_capture is None:
    print("\n" + "="*60)
    print("CAMERA TROUBLESHOOTING GUIDE:")
    print("1. Check camera connection: lsusb | grep -i camera")
    print("2. Check video devices: ls /dev/video*")
    print("3. Install drivers: sudo apt install v4l-utils cheese")
    print("4. Add user to video group: sudo usermod -a -G video $USER")
    print("5. Load camera driver: sudo modprobe uvcvideo")
    print("6. Test with cheese: cheese")
    print("7. Restart system after driver installation")
    print("="*60)
    print("[CRITICAL] Camera system failed to initialize!")
    sys.exit(1)

initialization_time = time.time() - start_time
print(f"[SUCCESS] Enhanced female voice camera system ready in {initialization_time:.2f} seconds")

# Warm up camera
print("[INFO] Warming up camera...")
for i in range(3):
    ret, _ = video_capture.read()
    if ret:
        break
    time.sleep(0.2)

print(f"[INFO] Tejgyan Face Recognition started for: {ACTIVE_SESSION.session_name}")
print(f"[INFO] Enhanced female voice system ready")
print("[INFO] Press 'q' to quit.")

# Main face recognition loop
try:
    while True:
        ret, frame = video_capture.read()
        if not ret:
            time.sleep(0.1)
            continue

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        now = time.time()

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matched_metadata = {
                "name": "Unknown", "email": "", "city": "", "shivir": "", "gender": "",
                "is_blacklisted": False, "is_active": True
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

                if email not in message_cache or now > message_cache[email]['visible_until']:
                    status_message = mark_attendance_with_ultra_voice(email, name, 'F')
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

            # Enhanced UI
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

            y_text = bottom + 20
            for line in info_lines:
                cv2.putText(frame, line, (left, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_text += 20

            # Status message display
            if status_message:
                message_width = max(200, len(status_message) * 8)
                
                if "wait" in status_message.lower() and ("hour" in status_message or "minute" in status_message):
                    bg_color = (0, 100, 150)
                    border_color = (0, 150, 255)
                    message_color = (255, 255, 255)
                elif "Session Already Completed" in status_message:
                    bg_color = (100, 0, 150)
                    border_color = (200, 0, 255)
                    message_color = (255, 255, 0)
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

            break

        # Clean up expired messages
        expired_emails = [email for email, data in message_cache.items() if now > data['visible_until']]
        for email in expired_emails:
            del message_cache[email]

        cv2.imshow(f"Tejgyan Foundation - Smart Voice Recognition System", frame)
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
    print("[INFO] Tejgyan Face Recognition System shutdown complete.")
