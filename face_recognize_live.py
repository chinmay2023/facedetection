# face_recognize_live.py
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
import io
from gtts import gTTS
import tempfile
import random

# Django setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "facerecognizer.settings")
django.setup()

from django.conf import settings
from faceapp.models import KnownPerson, Attendance, TejgyanSession  # ✅ ADDED: TejgyanSession import
from django.utils import timezone

# ✅ SUPPRESS PYGAME WELCOME MESSAGE
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# ✅ FIX QT PLUGIN WARNING
os.environ['QT_QPA_PLATFORM'] = 'xcb'

# Initialize pygame for premium audio playback
try:
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
    pygame.mixer.init()
except Exception as e:
    pass

# Voice system configuration
voice_queue = Queue()
USE_GTTS = True

# Initialize TTS engine
tts_engine = None
voice_initialized = False

def initialize_voice_engine():
    """Initialize TTS engine with Hindi support"""
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

def create_gtts_audio(text, gender='M'):
    """Create Google TTS audio file in Hindi"""
    try:
        tts = gTTS(text=text, lang='hi', slow=False, tld='co.in')
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts.save(tmp_file.name)
            return tmp_file.name
            
    except Exception as e:
        return None

def play_audio_file(audio_file):
    """Play audio file using pygame"""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            return True
        else:
            return False
            
    except Exception as e:
        return False

def speak_with_pyttsx3(text, gender='M'):
    """Speak using pyttsx3 engine"""
    global tts_engine, voice_initialized
    
    if not voice_initialized or not tts_engine:
        initialize_voice_engine()
    
    if voice_initialized and tts_engine:
        try:
            tts_engine.setProperty('rate', 150)
            tts_engine.setProperty('volume', 1.0)
            tts_engine.say(text)
            tts_engine.runAndWait()
            return True
        except Exception as e:
            return False
    else:
        return False

def voice_worker():
    """Voice worker thread for processing speech messages"""
    while True:
        try:
            voice_data = voice_queue.get(timeout=2)
            
            if voice_data == "STOP":
                break
            
            message, gender = voice_data
            success = False
            
            if USE_GTTS:
                audio_file = create_gtts_audio(message, gender)
                if audio_file:
                    if play_audio_file(audio_file):
                        success = True
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
            
            if not success:
                speak_with_pyttsx3(message, gender)
            
            voice_queue.task_done()
            time.sleep(0.5)
            
        except Exception as e:
            if str(e).strip() and "Empty" not in str(e):
                print(f"[WARNING] Voice error: {str(e)[:50]}")
            continue

def speak_ultra_clear(message, gender='M'):
    """Add message to voice queue"""
    try:
        voice_queue.put((message, gender), timeout=1)
    except Exception as e:
        pass

# ✅ NEW: Auto-detect active session from database
def get_active_session():
    """Fetch the current active session from database"""
    try:
        active_session = TejgyanSession.objects.get(is_active=True)
        return active_session
    except TejgyanSession.DoesNotExist:
        print("\n" + "="*60)
        print("⚠️  WARNING: No active session found in database!")
        print("📋 Please go to Django Admin and activate a session:")
        print("   1. Run: python manage.py runserver")
        print("   2. Visit: http://localhost:8000/admin/")
        print("   3. Go to 'Tejgyan Sessions'")
        print("   4. Create/Select a session and mark it as ACTIVE")
        print("="*60)
        return None
    except TejgyanSession.MultipleObjectsReturned:
        print("⚠️  WARNING: Multiple active sessions found! Fixing...")
        # Fix by keeping only the latest active session
        active_sessions = TejgyanSession.objects.filter(is_active=True).order_by('-created_at')
        latest_session = active_sessions.first()
        active_sessions.exclude(pk=latest_session.pk).update(is_active=False)
        return latest_session

# Initialize voice system
print("[INFO] Initializing Tejgyan Foundation Face Recognition System...")
initialize_voice_engine()

# Start voice worker thread
try:
    voice_thread = threading.Thread(target=voice_worker, daemon=True)
    voice_thread.start()
except Exception as e:
    print(f"[ERROR] Voice system failed: {e}")

# ✅ NEW: Get active session at startup
print("\nTejgyan Foundation Attendance System")
print("Conducted by: Sirshree")
print("="*50)

ACTIVE_SESSION = get_active_session()

if ACTIVE_SESSION:
    print(f"📅 Today's Active Session: {ACTIVE_SESSION.session_name}")
    print(f"📝 Session Type: {ACTIVE_SESSION.get_session_type_display()}")
    print(f"📅 Session Date: {ACTIVE_SESSION.session_date}")
    print(f"🙏 Conducted by: {ACTIVE_SESSION.conducted_by}")
    print("="*50)
else:
    print("❌ Cannot start face recognition without an active session!")
    print("Please activate a session in Django Admin first.")
    sys.exit(1)

# ✅ ENHANCED: Load ALL users (active, inactive, blacklisted)
known_face_encodings = []
known_face_metadata = []

# ✅ FIXED: Load ALL users regardless of status
people = KnownPerson.objects.all()

total_users = people.count()
active_users = people.filter(is_active=True).count()
inactive_users = people.filter(is_active=False).count()
blacklisted_users = people.filter(is_blacklisted=True).count()

# ✅ Enhanced: Show detailed statistics
print(f"[INFO] Loading face database:")
print(f"  Total users: {total_users}")
print(f"  Active: {active_users}")
print(f"  Inactive: {inactive_users}")
print(f"  Blacklisted: {blacklisted_users}")

loaded_encodings = 0
for person in people:
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

# ✅ FIXED: Session-specific voice messages with clear pronunciation
def get_session_specific_message(name, gender, session_type, status):
    """Generate session-specific Hindi voice messages with clear pronunciation"""
    
    # ✅ FIXED: Pronunciation-friendly session names
    session_names = {
        'MA': 'एम ए शिविर',                    # Clear phonetic spelling
        'SSP1': 'एस एस पी वन शिविर',              # Clear phonetic spelling
        'SSP2': 'एस एस पी टू शिविर',              # Clear phonetic spelling
        'HS1': 'हायर शिविर वन',                 # Higher Shivir One
        'HS2': 'हायर शिविर टू',                 # Higher Shivir Two
        'FESTIVAL': 'त्योहार सत्संग'             # Festival session (already clear)
    }
    
    session_hindi = session_names.get(session_type, 'शिविर')
    
    male_messages = {
        "first_attendance": [
            f"हैप्पी थॉट्स {name}, {session_hindi} में आपकी उपस्थिति सफलतापूर्वक दर्ज कर दी गई है, धन्यवाद।",
        ],
        "already_marked": [
            f"हैप्पी थॉट्स {name}, आज के {session_hindi} में आपकी उपस्थिति पहले से ही दर्ज है, धन्यवाद।",
        ]
    }
    
    female_messages = {
        "first_attendance": [
            f"हैप्पी थॉट्स {name}, {session_hindi} में आपकी उपस्थिति सफलतापूर्वक दर्ज कर दी गई है, धन्यवाद।",
        ],
        "already_marked": [
            f"हैप्पी थॉट्स {name}, आज के {session_hindi} में आपकी उपस्थिति पहले से ही दर्ज है, धन्यवाद।",
        ]
    }
    
    messages = female_messages if gender == 'F' else male_messages
    
    if status == "Attendance Marked Successfully!":
        return random.choice(messages["first_attendance"])
    elif status == "Attendance Already Marked!":
        return random.choice(messages["already_marked"])
    else:
        return f"स्वागत है {name}, {session_hindi} में आपका यहाँ होना अच्छा लगा।"

def get_ultra_clear_message(name, gender, status):
    """Generate Hindi voice messages for active users (fallback)"""
    return get_session_specific_message(name, gender, ACTIVE_SESSION.session_type if ACTIVE_SESSION else 'MA', status)

def get_blacklist_message(name, gender):
    """Generate Hindi blacklist notification messages"""
    male_messages = [
        f"हैप्पी थॉट्स {name}, आप वर्तमान में प्रतिबंधित सूची में हैं। कृपया एडमिन से संपर्क करें।",
    ]
    
    female_messages = [
        f"हैप्पी थॉट्स {name}, आप वर्तमान में प्रतिबंधित सूची में हैं। कृपया एडमिन से संपर्क करें।",
    ]
    
    messages = female_messages if gender == 'F' else male_messages
    return random.choice(messages)

def get_inactive_message(name, gender):
    """Generate Hindi messages for inactive users"""
    male_messages = [
        f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय हैं। कृपया एडमिन से संपर्क करके सक्रियता प्राप्त करें।",
    ]
    
    female_messages = [
        f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय हैं। कृपया एडमिन से संपर्क करके सक्रियता प्राप्त करें।",
    ]
    
    messages = female_messages if gender == 'F' else male_messages
    return random.choice(messages)

def get_inactive_and_blacklisted_message(name, gender):
    """Generate Hindi messages for users who are both inactive and blacklisted"""
    male_messages = [
        f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय और प्रतिबंधित सूची दोनों में हैं। कृपया तुरंत एडमिन से संपर्क करें।",
    ]
    
    female_messages = [
        f"हैप्पी थॉट्स {name}, आप वर्तमान में निष्क्रिय और प्रतिबंधित सूची दोनों में हैं। कृपया तुरंत एडमिन से संपर्क करें।",
    ]
    
    messages = female_messages if gender == 'F' else male_messages
    return random.choice(messages)

# ✅ ENHANCED: Updated attendance function with automatic session detection
def mark_attendance_with_ultra_voice(email, name, gender):
    """Enhanced attendance marking with automatic session detection"""
    try:
        matched_person = KnownPerson.objects.get(email=email)
    except KnownPerson.DoesNotExist:
        return None

    # ✅ Handle users who are BOTH inactive AND blacklisted
    if not matched_person.is_active and matched_person.is_blacklisted:
        status = "User is Inactive & Blacklisted!"
        voice_message = get_inactive_and_blacklisted_message(name, gender)
        speak_ultra_clear(voice_message, gender)
        return status

    # ✅ Handle ONLY inactive users (not blacklisted)
    elif not matched_person.is_active:
        status = "User is Inactive!"
        voice_message = get_inactive_message(name, gender)
        speak_ultra_clear(voice_message, gender)
        return status

    # ✅ Handle ONLY blacklisted users (but active)
    elif matched_person.is_blacklisted:
        status = "User is Blacklisted!"
        voice_message = get_blacklist_message(name, gender)
        speak_ultra_clear(voice_message, gender)
        return status

    # ✅ NEW: Handle normal active users with session-specific attendance
    else:
        today = timezone.now().date()
        
        # ✅ Check if already marked attendance for this session today
        already_marked = Attendance.objects.filter(
            person=matched_person, 
            session=ACTIVE_SESSION,
            timestamp__date=today
        ).exists()
        
        if not already_marked:
            # ✅ Create attendance record with active session
            Attendance.objects.create(
                person=matched_person,
                session=ACTIVE_SESSION
            )
            status = f"Attendance Marked for {ACTIVE_SESSION.get_session_type_display()}!"
            voice_message = get_session_specific_message(name, gender, ACTIVE_SESSION.session_type, "Attendance Marked Successfully!")
            speak_ultra_clear(voice_message, gender)
            return status
        else:
            status = f"Already marked for {ACTIVE_SESSION.get_session_type_display()}!"
            if np.random.random() < 0.3:
                voice_message = get_session_specific_message(name, gender, ACTIVE_SESSION.session_type, "Attendance Already Marked!")
                speak_ultra_clear(voice_message, gender)
            return status

# ✅ Enhanced: Color coding for all user combinations
def get_user_color(metadata):
    """Get color based on user status combination"""
    if metadata['name'] == "Unknown":
        return (0, 0, 255)  # Red for unknown
    
    is_inactive = not metadata.get('is_active', True)
    is_blacklisted = metadata.get('is_blacklisted', False)
    
    if is_inactive and is_blacklisted:
        return (0, 0, 139)  # Dark red for both statuses
    elif is_blacklisted:
        return (0, 0, 255)  # Red for blacklisted only
    elif is_inactive:
        return (0, 165, 255)  # Orange for inactive only
    else:
        # Normal active users
        return (255, 0, 255) if metadata['gender'] == 'F' else (0, 255, 0)

# ✅ Enhanced: Status display for all combinations
def get_status_display(metadata):
    if metadata['name'] == "Unknown":
        return "Unknown Person"
    
    is_inactive = not metadata.get('is_active', True)
    is_blacklisted = metadata.get('is_blacklisted', False)
    
    if is_inactive and is_blacklisted:
        return "INACTIVE & BLACKLISTED"
    elif is_blacklisted:
        return "BLACKLISTED"
    elif is_inactive:
        return "INACTIVE"
    else:
        return "Active"

def get_gender_display(gender):
    if gender == 'F':
        return 'Female'
    elif gender == 'M':
        return 'Male'
    else:
        return ''

# Cache management
message_cache = {}
MESSAGE_DISPLAY_SECONDS = 4

# Video capture setup
video_capture = cv2.VideoCapture(0)
if not video_capture.isOpened():
    print("[ERROR] Could not open webcam.")
    sys.exit(1)

video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print(f"[INFO] Tejgyan Face Recognition started for: {ACTIVE_SESSION.session_name}")
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

                # ✅ Enhanced: Handle ALL user types with proper messages
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

            # ✅ Enhanced: Use new color function for all user combinations
            color = get_user_color(matched_metadata)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # ✅ Enhanced: Show proper status for all user types with session info
            info_lines = [
                f"Name: {matched_metadata['name']}",
                f"Gender: {get_gender_display(matched_metadata['gender'])}",
                f"Email: {matched_metadata['email']}",
                f"City: {matched_metadata['city']}",
                f"Shivir: {matched_metadata['shivir']}",
                f"Status: {get_status_display(matched_metadata)}"
            ]
            
            # ✅ NEW: Add active session info to display
            if ACTIVE_SESSION and matched_metadata['name'] != "Unknown":
                info_lines.append(f"Session: {ACTIVE_SESSION.session_type}")

            # Display info
            y_text = bottom + 20
            for line in info_lines:
                cv2.putText(frame, line, (left, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_text += 20

            # ✅ Enhanced: Status-specific message colors for all combinations
            if status_message:
                message_width = max(200, len(status_message) * 8)
                
                if "Inactive & Blacklisted" in status_message:
                    bg_color = (0, 0, 80)      # Dark red background
                    border_color = (0, 0, 139)  # Dark red border
                    message_color = (255, 255, 255)
                elif "Blacklisted" in status_message:
                    bg_color = (0, 0, 100)
                    border_color = (0, 0, 255)
                    message_color = (255, 255, 255)
                elif "Inactive" in status_message:
                    bg_color = (0, 80, 100)  # Orange background
                    border_color = (0, 165, 255)  # Orange border
                    message_color = (255, 255, 255)
                elif matched_metadata['gender'] == 'F':
                    bg_color = (100, 0, 100)
                    border_color = (255, 0, 255)
                    message_color = (255, 255, 0) if "Successfully" in status_message else (0, 255, 255)
                else:
                    bg_color = (0, 100, 0)
                    border_color = (0, 255, 0)
                    message_color = (255, 255, 0) if "Successfully" in status_message else (0, 255, 255)
                
                cv2.rectangle(frame, (left, y_text + 5), (left + message_width, y_text + 35), bg_color, -1)
                cv2.rectangle(frame, (left, y_text + 5), (left + message_width, y_text + 35), border_color, 2)
                cv2.putText(frame, status_message, (left + 5, y_text + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, message_color, 2)

        # Clean up expired messages
        expired_emails = [email for email, data in message_cache.items() if now > data['visible_until']]
        for email in expired_emails:
            del message_cache[email]

        cv2.imshow("Tejgyan Foundation - Face Recognition Attendance", frame)
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
