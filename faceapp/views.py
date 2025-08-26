# faceapp/views.py - ENHANCED WITH ALL FACE_RECOGNIZE_LIVE.PY FEATURES INTEGRATED
# 🔧 COMPLETELY FIXED: Flexible renewal time logic that works with ANY interval
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from django.db import IntegrityError
import json
import base64
import io
import numpy as np
from PIL import Image
import face_recognition
import logging
from datetime import date, timedelta

# Enhanced model imports
from .models import (
    KnownPerson, TejgyanSession, Attendance,
    MA_Attendance, SSP1_Attendance, SSP2_Attendance, 
    HS1_Attendance, HS2_Attendance,
    MA_Repeaters, SSP1_Repeaters, SSP2_Repeaters, 
    HS1_Repeaters, HS2_Repeaters
)

from .hindi_messages import (
    get_person_not_found_message,
    get_blacklist_message,
    get_inactive_message,
    get_inactive_and_blacklisted_message,
    get_no_session_message,
    get_system_error_message,
    get_attendance_marked_message,
    get_already_marked_message
)

try:
    from .utils import encode_face_image
except ImportError:
    def encode_face_image(image):
        return None

try:
    from .voice_helper import speak
except ImportError:
    def speak(message):
        print(f"Voice: {message}")

logger = logging.getLogger(__name__)

# ================================
# 🚀 ENHANCED UTILITY FUNCTIONS FROM FACE_RECOGNIZE_LIVE.PY
# ================================

# 🔧 COMPLETELY FIXED: Flexible attendance renewal configuration
ATTENDANCE_RENEWAL_HOURS = 0.0167    # 🔧 CONFIGURABLE: Set to any value you want!
                                     # 0.0028 = 10 seconds (for testing)
                                     # 0.0167 = 1 minute (recommended for testing)
                                     # 0.0833 = 5 minutes
                                     # 0.5 = 30 minutes
                                     # 1.0 = 1 hour
                                     # 12.0 = 12 hours (production)

MESSAGE_DISPLAY_SECONDS = 30     # Visual message display duration
VOICE_REPEAT_SECONDS = 3         # Voice repeats every 3 seconds
MAX_VOICE_REPEATS = 3            # Maximum voice repeats for success/already marked

# Voice repetition modes
VOICE_MODE_SUCCESS = "success"           # 3 times then stop
VOICE_MODE_ALREADY_MARKED = "already"    # 3 times then stop
VOICE_MODE_WAIT_NEXT_DAY = "wait"        # Infinite until user leaves

def get_attendance_model(session_type):
    """Get the appropriate attendance model for session type"""
    models_map = {
        'MA': MA_Attendance, 'SSP1': SSP1_Attendance, 'SSP2': SSP2_Attendance,
        'HS1': HS1_Attendance, 'HS2': HS2_Attendance,
    }
    return models_map.get(session_type)

def get_repeater_model(session_type):
    """Get the appropriate repeater model for session type"""
    models_map = {
        'MA': MA_Repeaters, 'SSP1': SSP1_Repeaters, 'SSP2': SSP2_Repeaters,
        'HS1': HS1_Repeaters, 'HS2': HS2_Repeaters,
    }
    return models_map.get(session_type)

def get_session_duration(session_type):
    """Get duration for each session type"""
    durations = {
        'MA': 5, 'SSP1': 2, 'SSP2': 2, 'HS1': 2, 'HS2': 2, 'FESTIVAL': 1
    }
    return durations.get(session_type, 1)

def get_user_eligible_sessions(person, user_shivir_level):
    """Get sessions user is eligible for based on shivir background"""
    progression_order = ['MA', 'SSP1', 'SSP2', 'HS1', 'HS2']
    eligible_sessions = []
    
    if not user_shivir_level:
        eligible_sessions = ['MA']
    else:
        try:
            current_level_index = progression_order.index(user_shivir_level)
            # Add all previous levels + current level + next level
            for i in range(current_level_index + 1):
                eligible_sessions.append(progression_order[i])
            if current_level_index + 1 < len(progression_order):
                next_level = progression_order[current_level_index + 1]
                eligible_sessions.append(next_level)
        except ValueError:
            eligible_sessions = ['MA']
    
    # Add FESTIVAL for everyone
    if 'FESTIVAL' not in eligible_sessions:
        eligible_sessions.append('FESTIVAL')
    
    return eligible_sessions

def check_advanced_attendance_renewal(person, active_session):
    """🚨 COMPLETELY FIXED: Bulletproof renewal logic that works with ANY time interval"""
    
    print(f"\n🚨 RENEWAL DEBUG for {person.name}")
    print(f"🚨 Config: ATTENDANCE_RENEWAL_HOURS = {ATTENDANCE_RENEWAL_HOURS}")
    print(f"🚨 Current time: {timezone.now()}")
    
    # Get the most recent attendance for this person and session
    last_attendance = Attendance.objects.filter(
        person=person, 
        session=active_session
    ).order_by('-timestamp').first()
    
    if not last_attendance:
        print(f"✅ No previous attendance found - ALLOW")
        return True, "can_mark", 0, None
    
    # Calculate time difference using timezone-aware comparison
    now = timezone.now()
    time_diff = now - last_attendance.timestamp
    
    # Convert to seconds for precision
    seconds_passed = time_diff.total_seconds()
    required_seconds = ATTENDANCE_RENEWAL_HOURS * 3600
    
    print(f"🚨 Last attendance: {last_attendance.timestamp}")
    print(f"🚨 Current time: {now}")
    print(f"🚨 Time difference: {time_diff}")
    print(f"🚨 Seconds passed: {seconds_passed:.2f}")
    print(f"🚨 Required seconds: {required_seconds:.2f}")
    
    if seconds_passed >= required_seconds:
        print(f"✅ Time passed ({seconds_passed:.2f}s >= {required_seconds:.2f}s) - ALLOW")
        return True, "can_mark", seconds_passed/3600, last_attendance
    else:
        remaining_seconds = required_seconds - seconds_passed
        print(f"❌ Still in cooldown - {remaining_seconds:.2f}s remaining - BLOCK")
        
        # 🔧 FIXED: Flexible "just marked" detection based on configured time
        if remaining_seconds <= (required_seconds * 0.1):  # Within 10% of renewal time
            return False, "just_marked", remaining_seconds/3600, last_attendance
        else:
            return False, "in_cooldown", remaining_seconds/3600, last_attendance

def check_if_repeat_attendance(person, session_type, today, active_session):
    """Check if this is a repeat attendance with 1-day minimum gap"""
    if session_type == 'FESTIVAL':
        return False, None
    
    AttendanceModel = get_attendance_model(session_type)
    if not AttendanceModel:
        return False, None
    
    # Check if there's an ACTIVE/ONGOING session
    active_session_attendance = AttendanceModel.objects.filter(
        person=person,
        session_reference=active_session,
        is_completed=False  # Not completed yet
    ).first()
    
    if active_session_attendance:
        # Person has an ongoing session - NOT a repeater
        return False, None
    
    # Check for completed sessions with 1-day minimum gap requirement
    completed_attendance = AttendanceModel.objects.filter(
        person=person, 
        is_completed=True
    ).order_by('-attendance_date').first()
    
    if completed_attendance:
        last_completion_date = completed_attendance.attendance_date
        RepeaterModel = get_repeater_model(session_type)
        if RepeaterModel:
            last_repeat = RepeaterModel.objects.filter(
                person=person
            ).order_by('-repeat_attendance_date').first()
            if last_repeat:
                last_completion_date = last_repeat.repeat_attendance_date
        
        days_gap = (today - last_completion_date).days
        
        # Only allow repeat attendance if at least 1 day has passed
        if days_gap >= 1:
            return True, {
                'last_completion_date': last_completion_date, 
                'days_gap': days_gap
            }
        else:
            # Same day completion - not eligible for repeat yet
            return False, None
    
    return False, None

def create_repeater_record_safely(RepeaterModel, person, last_completion_date, days_gap, active_session):
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
            repeat_count=repeat_count,
            session_reference=active_session
        )
        return repeater, True  # Successfully created
    except IntegrityError:
        # Handle race condition
        existing = RepeaterModel.objects.filter(
            person=person,
            repeat_attendance_date=today
        ).first()
        return existing, False  # Already exists

# ================================
# 🔥 ENHANCED HINDI VOICE MESSAGES WITH SESSION & DAY INFO
# ================================

def get_day_attendance_marked_message(name, session_type, day_number, session_duration):
    """Enhanced message with session name and day information"""
    session_names = {
        'MA': 'एम ए शिविर', 'SSP1': 'एस एस पी वन शिविर', 'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन', 'HS2': 'हायर शिविर टू', 'FESTIVAL': 'त्योहार सत्संग'
    }
    session_hindi = session_names.get(session_type, 'शिविर')
    
    if day_number == session_duration:
        return f"हैप्पी थॉट्स {name}, {session_hindi} के अंतिम दिन {day_number} की उपस्थिति सफलतापूर्वक दर्ज हो गई है। आपके भावी सत्र के लिए शुभकामनाएं, धन्यवाद।"
    else:
        return f"हैप्पी थॉट्स {name}, {session_hindi} के दिन {day_number} की उपस्थिति सफलतापूर्वक दर्ज हो गई है, धन्यवाद।"

def get_session_already_completed_message(name, session_type):
    session_names = {
        'MA': 'एम ए शिविर', 'SSP1': 'एस एस पी वन शिविर', 'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन', 'HS2': 'हायर शिविर टू', 'FESTIVAL': 'त्योहार सत्संग'
    }
    session_hindi = session_names.get(session_type, 'शिविर')
    return f"हैप्पी थॉट्स {name}, {session_hindi} में आपकी उपस्थिति सफलतापूर्वक दर्ज हो गई है। कृपया अगले शिविर के लिए भविष्य में आएं, धन्यवाद।"

def get_new_user_guidance_message(name):
    return f"हैप्पी थॉट्स {name}, तेजज्ञान फाउंडेशन में आपका हार्दिक स्वागत है। कृपया पहले एम ए शिविर से अपनी आध्यात्मिक यात्रा शुरू करें, धन्यवाद।"

def get_not_eligible_message(name, current_session, user_level):
    session_names = {
        'MA': 'एम ए शिविर', 'SSP1': 'एस एस पी वन शिविर', 'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन', 'HS2': 'हायर शिविर टू', 'FESTIVAL': 'त्योहार सत्संग'
    }
    current_hindi = session_names.get(current_session, 'शिविर')
    return f"हैप्पी थॉट्स {name}, आप {current_hindi} के लिए योग्य नहीं हैं, कृपया पहले पिछला स्तर पूरा करें, धन्यवाद।"

def get_mark_next_day_message(name, hours_remaining):
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति दर्ज हो चुकी है। कृपया अगले दिन उपस्थिति दर्ज करें, धन्यवाद।"

def get_repeater_welcome_message(name, days_gap):
    return f"हैप्पी थॉट्स {name}, {days_gap} दिन बाद आपका पुनरागमन अत्यंत स्वागत है। आपकी निरंतर साधना प्रेरणादायक है, आपकी उपस्थिति दर्ज की गई है, धन्यवाद।"

def get_repeater_already_marked_message(name):
    return f"हैप्पी थॉट्स {name}, आपकी उपस्थिति पहले से ही दर्ज है, आपकी निरंतरता सराहनीय है, धन्यवाद।"

def get_current_state_voice_message(email, name, session_type):
    """Get live voice message based on current user state for repetition"""
    try:
        matched_person = KnownPerson.objects.get(email=email)
        
        # Check current state and return appropriate message
        if not matched_person.is_active and matched_person.is_blacklisted:
            return get_inactive_and_blacklisted_message(name), VOICE_MODE_WAIT_NEXT_DAY
        elif not matched_person.is_active:
            return get_inactive_message(name), VOICE_MODE_WAIT_NEXT_DAY
        elif matched_person.is_blacklisted:
            return get_blacklist_message(name), VOICE_MODE_WAIT_NEXT_DAY
        
        # Check attendance eligibility
        today = date.today()
        user_shivir_level = matched_person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(matched_person, user_shivir_level)
        
        if session_type not in eligible_sessions:
            if not user_shivir_level:
                return get_new_user_guidance_message(name), VOICE_MODE_WAIT_NEXT_DAY
            else:
                return get_not_eligible_message(name, session_type, user_shivir_level), VOICE_MODE_WAIT_NEXT_DAY
        
        # Check 12-hour renewal status
        active_session = TejgyanSession.objects.filter(is_active=True).first()
        can_mark_general, renewal_state, hours_remaining, last_attendance = check_advanced_attendance_renewal(matched_person, active_session)
        
        if not can_mark_general:
            if renewal_state == "just_marked":
                # Check current day for specific message including session name and day
                if session_type != 'FESTIVAL':
                    AttendanceModel = get_attendance_model(session_type)
                    if AttendanceModel:
                        existing_attendance = AttendanceModel.objects.filter(
                            person=matched_person,
                            session_reference=active_session
                        ).first()
                        if existing_attendance:
                            session_duration = get_session_duration(session_type)
                            return get_day_attendance_marked_message(name, session_type, existing_attendance.day_number, session_duration), VOICE_MODE_ALREADY_MARKED
                
                return get_already_marked_message(name), VOICE_MODE_ALREADY_MARKED
            else:
                # In 12-hour cooldown period - infinite voice repetition
                return get_mark_next_day_message(name, hours_remaining), VOICE_MODE_WAIT_NEXT_DAY
        else:
            return get_attendance_marked_message(name, session_type), VOICE_MODE_SUCCESS
            
    except Exception as e:
        return get_attendance_marked_message(name, session_type), VOICE_MODE_SUCCESS

# ================================
# 🚀 EXISTING VIEWS WITH ENHANCED FUNCTIONALITY
# ================================

def attendance_interface(request):
    """
    Render the main face recognition attendance interface
    """
    try:
        active_session = TejgyanSession.objects.filter(is_active=True).first()
        today = timezone.localdate()
        
        context = {
            'active_session': active_session,
            'session_name': active_session.session_name if active_session else 'No Active Session',
            'session_type': active_session.session_type if active_session else 'None',
            'conducted_by': active_session.conducted_by if active_session else 'Unknown',
            'today_attendance': Attendance.objects.filter(timestamp__date=today).count(),
            'active_users': KnownPerson.objects.filter(is_active=True, is_blacklisted=False).count(),
            'current_date': today.strftime('%B %d, %Y'),
        }
        
        logger.info("Rendering attendance interface successfully")
        return render(request, 'faceapp/attendance.html', context)
        
    except Exception as e:
        logger.error(f"Error in attendance_interface: {e}")
        context = {
            'active_session': None,
            'session_name': 'System Error',
            'session_type': 'None',
            'conducted_by': 'System',
            'today_attendance': 0,
            'active_users': 0,
            'current_date': timezone.localdate().strftime('%B %d, %Y'),
            'error_message': 'Please contact administrator'
        }
        return render(request, 'faceapp/attendance.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def recognize_face_api(request):
    """
    🚀 ENHANCED: Face recognition API with advanced user state detection and voice system integration
    """
    try:
        # 🚨 DEBUG: Confirm new code is running
        print("🚨 ENHANCED FACE RECOGNITION API CALLED!")
        print(f"🚨 ATTENDANCE_RENEWAL_HOURS = {ATTENDANCE_RENEWAL_HOURS}")
        
        logger.info("Enhanced face recognition API called")
        
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            logger.warning("No image data provided")
            return JsonResponse({
                'success': False,
                'error_type': 'no_image',
                'message': 'No image data provided',
                'hindi_voice_message': 'कृपया अपनी तस्वीर प्रदान करें, धन्यवाद।',
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            })
        
        face_encoding = process_webcam_image(image_data)
        
        if face_encoding is None:
            logger.info("No face detected in image")
            return JsonResponse({
                'success': False,
                'error_type': 'face_not_found',
                'message': 'No face detected in image',
                'hindi_voice_message': 'कृपया अपना चेहरा कैमरे के सामने स्पष्ट रूप से दिखाएं, धन्यवाद।',
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            })
        
        recognized_person = find_matching_person(face_encoding)
        
        if not recognized_person:
            logger.info("🔒 SECURITY: Face not recognized - Unknown person detected")
            return JsonResponse({
                'success': False,
                'error_type': 'person_not_recognized',
                'message': 'Face not recognized. Please register first.',
                'hindi_voice_message': get_person_not_found_message(),
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            })
        
        logger.info(f"Person recognized: {recognized_person.name}")
        
        # 🚀 ENHANCED: Check person status with advanced state detection
        if not recognized_person.is_active and recognized_person.is_blacklisted:
            logger.warning(f"Person {recognized_person.name} is inactive and blacklisted")
            return JsonResponse({
                'success': False,
                'error_type': 'person_inactive_blacklisted',
                'message': 'Account is inactive and blacklisted. Contact administrator.',
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_inactive_and_blacklisted_message(recognized_person.name),
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            })
        
        if not recognized_person.is_active:
            logger.warning(f"Person {recognized_person.name} is inactive")
            return JsonResponse({
                'success': False,
                'error_type': 'person_inactive',
                'message': 'Account inactive. Contact administrator.',
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_inactive_message(recognized_person.name),
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            })
        
        if recognized_person.is_blacklisted:
            logger.warning(f"Person {recognized_person.name} is blacklisted")
            return JsonResponse({
                'success': False,
                'error_type': 'person_blacklisted',
                'message': 'Access denied. Contact administrator.',
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_blacklist_message(recognized_person.name),
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            })
        
        try:
            active_session = TejgyanSession.objects.filter(is_active=True).first()
        except Exception:
            active_session = None
            
        if not active_session:
            logger.warning("No active session found")
            return JsonResponse({
                'success': False,
                'error_type': 'no_active_session',
                'message': 'No active session found. Contact administrator.',
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_no_session_message(recognized_person.name),
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            })
        
        # 🚀 ENHANCED: Check user eligibility based on shivir background
        user_shivir_level = recognized_person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(recognized_person, user_shivir_level)
        session_type = active_session.session_type
        
        if session_type not in eligible_sessions:
            if not user_shivir_level:
                return JsonResponse({
                    'success': False,
                    'error_type': 'new_user_not_eligible',
                    'message': 'New user - Must start with MA Shivir.',
                    'user_data': get_user_display_data(recognized_person, active_session),
                    'hindi_voice_message': get_new_user_guidance_message(recognized_person.name),
                    'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error_type': 'not_eligible_for_session',
                    'message': f'Not eligible for {session_type}. Complete previous sessions first.',
                    'user_data': get_user_display_data(recognized_person, active_session),
                    'hindi_voice_message': get_not_eligible_message(recognized_person.name, session_type, user_shivir_level),
                    'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
                })
        
        # 🔧 COMPLETELY FIXED: Advanced attendance renewal status check
        can_mark, renewal_state, hours_remaining, last_attendance = check_advanced_attendance_renewal(recognized_person, active_session)
        
        if not can_mark:
            if renewal_state == "just_marked":
                voice_message, voice_mode = get_current_state_voice_message(recognized_person.email, recognized_person.name, session_type)
                return JsonResponse({
                    'success': False,
                    'error_type': 'just_marked',
                    'message': 'Attendance already marked moments ago.',
                    'user_data': get_user_display_data(recognized_person, active_session),
                    'renewal_info': {
                        'state': renewal_state,
                        'hours_remaining': hours_remaining,
                        'seconds_remaining': int(hours_remaining * 3600),
                        'last_attendance': last_attendance.timestamp.isoformat() if last_attendance else None
                    },
                    'hindi_voice_message': voice_message,
                    'voice_mode': voice_mode
                })
            else:
                # 🔧 FIXED: Show appropriate time units based on renewal period
                if ATTENDANCE_RENEWAL_HOURS < 1.0:  # Less than 1 hour
                    if hours_remaining < 0.0167:  # Less than 1 minute
                        seconds_remaining = int(hours_remaining * 3600)
                        status_msg = f"Please wait {seconds_remaining} seconds before next attendance"
                    else:
                        minutes_remaining = int(hours_remaining * 60)
                        status_msg = f"Please wait {minutes_remaining} minutes before next attendance"
                else:  # 1 hour or more
                    if hours_remaining > 1:
                        status_msg = f"Please wait {hours_remaining:.1f} hours before next attendance"
                    else:
                        minutes_remaining = int(hours_remaining * 60)
                        status_msg = f"Please wait {minutes_remaining} minutes before next attendance"
                
                voice_message, voice_mode = get_current_state_voice_message(recognized_person.email, recognized_person.name, session_type)
                return JsonResponse({
                    'success': False,
                    'error_type': 'in_cooldown',
                    'message': status_msg,
                    'user_data': get_user_display_data(recognized_person, active_session),
                    'renewal_info': {
                        'state': renewal_state,
                        'hours_remaining': hours_remaining,
                        'seconds_remaining': int(hours_remaining * 3600),
                        'renewal_config': {
                            'hours': ATTENDANCE_RENEWAL_HOURS,
                            'seconds': int(ATTENDANCE_RENEWAL_HOURS * 3600),
                        },
                        'last_attendance': last_attendance.timestamp.isoformat() if last_attendance else None
                    },
                    'hindi_voice_message': voice_message,
                    'voice_mode': voice_mode
                })
        
        # 🚀 ENHANCED: Check if this is a repeat attendance
        today = timezone.now().date()
        is_repeat, repeat_info = check_if_repeat_attendance(recognized_person, session_type, today, active_session)
        
        user_data = get_user_display_data(recognized_person, active_session)
        
        # Add enhanced user state information
        user_data.update({
            'shivir_background_level': user_shivir_level,
            'eligible_sessions': eligible_sessions,
            'is_eligible_for_current': session_type in eligible_sessions,
            'renewal_status': {
                'can_mark': can_mark,
                'state': renewal_state,
                'hours_remaining': hours_remaining,
                'seconds_remaining': int(hours_remaining * 3600) if hours_remaining else 0
            },
            'is_repeat_eligible': is_repeat,
            'repeat_info': repeat_info if is_repeat else None
        })
        
        logger.info(f"Successfully recognized {recognized_person.name} with enhanced state detection")
        
        return JsonResponse({
            'success': True,
            'user_data': user_data,
            'session_info': {
                'id': active_session.id,
                'name': active_session.session_name,
                'type': active_session.session_type,
                'conducted_by': active_session.conducted_by,
                'duration': get_session_duration(active_session.session_type)
            },
            'voice_system': {
                'repeat_interval': VOICE_REPEAT_SECONDS,
                'max_repeats': MAX_VOICE_REPEATS,
                'modes': {
                    'success': VOICE_MODE_SUCCESS,
                    'already_marked': VOICE_MODE_ALREADY_MARKED,
                    'wait_next_day': VOICE_MODE_WAIT_NEXT_DAY
                }
            }
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {e}")
        return JsonResponse({
            'success': False,
            'error_type': 'invalid_data',
            'message': 'Invalid JSON data',
            'hindi_voice_message': 'डेटा में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।',
            'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
        })
    except Exception as e:
        logger.error(f"Error in enhanced recognize_face_api: {e}")
        return JsonResponse({
            'success': False,
            'error_type': 'system_error',
            'message': 'System error occurred. Please try again.',
            'hindi_voice_message': get_system_error_message('उपयोगकर्ता'),
            'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
        })

def process_webcam_image(image_data):
    """
    Process base64 image data from webcam and extract face encoding
    """
    try:
        logger.info("Processing webcam image")
        
        if 'data:image' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        image_array = np.array(image)
        face_encodings = face_recognition.face_encodings(image_array)
        
        if face_encodings:
            logger.info(f"Found {len(face_encodings)} face(s) in image")
            return face_encodings[0]
        else:
            logger.info("No faces found in image")
            return None
            
    except Exception as e:
        logger.error(f"Error processing webcam image: {e}")
        return None

def find_matching_person(face_encoding, tolerance=0.6):
    """
    Find matching person with proper unknown detection
    """
    try:
        logger.info("🔍 Searching for matching person in database")
        
        known_persons = KnownPerson.objects.filter(
            is_active=True,
            is_blacklisted=False,
            encoding__isnull=False
        )
        
        logger.info(f"👥 Checking against {known_persons.count()} known persons with encodings")
        
        if known_persons.count() == 0:
            logger.warning("❌ No persons with face encodings found in database")
            return None
        
        best_match = None
        best_distance = float('inf')
        
        for person in known_persons:
            try:
                if not person.encoding:
                    logger.warning(f"⚠️ {person.name} has no face encoding")
                    continue
                
                try:
                    stored_encoding = np.frombuffer(person.encoding, dtype=np.float64)
                    logger.info(f"📊 Loaded encoding for {person.name}: {len(stored_encoding)} features")
                except Exception as encoding_error:
                    logger.error(f"❌ Failed to load encoding for {person.name}: {encoding_error}")
                    continue
                
                try:
                    distances = face_recognition.face_distance([stored_encoding], face_encoding)
                    distance = distances[0]
                    
                    logger.info(f"📏 Distance for {person.name}: {distance:.4f} (tolerance: {tolerance})")
                    
                    if distance <= tolerance:
                        logger.info(f"✅ POTENTIAL MATCH: {person.name} (distance: {distance:.4f})")
                        
                        if distance < best_distance:
                            best_match = person
                            best_distance = distance
                            logger.info(f"🎯 NEW BEST MATCH: {person.name} (distance: {distance:.4f})")
                    else:
                        logger.info(f"❌ No match for {person.name} (distance: {distance:.4f} > tolerance: {tolerance})")
                        
                except Exception as comparison_error:
                    logger.error(f"❌ Error comparing faces for {person.name}: {comparison_error}")
                    continue
                    
            except Exception as person_error:
                logger.error(f"❌ Error processing person {person.name}: {person_error}")
                continue
        
        if best_match and best_distance <= tolerance:
            confidence_threshold = 0.55
            
            if best_distance <= confidence_threshold:
                logger.info(f"🎉 HIGH CONFIDENCE MATCH: {best_match.name} (distance: {best_distance:.4f})")
                return best_match
            elif best_distance <= tolerance:
                logger.warning(f"⚠️ LOW CONFIDENCE MATCH: {best_match.name} (distance: {best_distance:.4f})")
                logger.warning(f"🚫 REJECTED: Distance {best_distance:.4f} > confidence threshold {confidence_threshold}")
                return None
            else:
                logger.info(f"❌ MATCH REJECTED: {best_match.name} (distance: {best_distance:.4f} > tolerance: {tolerance})")
                return None
        else:
            logger.info(f"❌ NO MATCHING PERSON FOUND - CORRECTLY IDENTIFYING AS UNKNOWN")
            logger.info(f"📊 Best distance was: {best_distance:.4f} (needed: ≤ {tolerance})")
            logger.info(f"🔒 SECURITY: Properly returning None for unknown face")
            return None
        
    except Exception as e:
        logger.error(f"❌ Critical error in find_matching_person: {e}")
        return None

def get_user_display_data(person, session=None):
    """
    Get user data for display in the form
    """
    try:
        try:
            spiritual_level = getattr(person, 'shivir', None) or 'New User'
        except:
            spiritual_level = 'New User'
        
        session_info = 'No Active Session'
        if session:
            session_info = f"{session.session_name} ({session.session_type})"
        
        if not person.is_active:
            reason = getattr(person, 'deactivated_reason', None)
            status = f"❌ Inactive" + (f" - {reason}" if reason else "")
        elif person.is_blacklisted:
            reason = getattr(person, 'blacklisted_reason', None)
            status = f"🚫 Blacklisted" + (f" - {reason}" if reason else "")
        else:
            status = "✅ Active Member"
        
        user_data = {
            'name': person.name or 'Unknown',
            'email': person.email or 'Unknown',
            'city': person.city or 'Unknown',
            'shivir_level': spiritual_level,
            'status': status,
            'current_session': session_info
        }
        
        logger.info(f"📝 Generated user display data for {person.name}")
        return user_data
        
    except Exception as e:
        logger.error(f"Error getting user display data: {e}")
        return {
            'name': getattr(person, 'name', 'Unknown'),
            'email': getattr(person, 'email', 'Unknown'),
            'city': getattr(person, 'city', 'Unknown'),
            'shivir_level': 'Error loading data',
            'status': 'Error',
            'current_session': 'Error'
        }

def get_session_max_days(session_type):
    """
    Get maximum days for each session type
    """
    session_days = {
        'MA': 5, 'SSP1': 2, 'SSP2': 2, 'HS1': 2, 'HS2': 2, 'FESTIVAL': 1
    }
    return session_days.get(session_type, 1)

def get_hindi_session_name(session_type):
    """
    Get Hindi session names
    """
    hindi_names = {
        'MA': 'एम ए शिविर',
        'SSP1': 'एस एस पी वन शिविर',
        'SSP2': 'एस एस पी टू शिविर',
        'HS1': 'हायर शिविर वन',
        'HS2': 'हायर शिविर टू',
        'FESTIVAL': 'फेस्टिवल सत्र'
    }
    return hindi_names.get(session_type, session_type)

def generate_hindi_attendance_message(person_name, session_type, day_number, is_last_day):
    """
    Generate day-specific Hindi TTS messages
    """
    hindi_session = get_hindi_session_name(session_type)
    
    if is_last_day:
        # Last day completion messages
        if session_type == 'MA':
            return f"हैप्पी थॉट्स {person_name}! {hindi_session} के दिन {day_number} की उपस्थिति सफलतापूर्वक दर्ज हो गई है। एम ए शिविर सफलतापूर्वक पूरा हो गया है। एस एस पी वन शिविर के लिए शुभकामनाएं, धन्यवाद।"
        elif session_type == 'SSP1':
            return f"हैप्पी थॉट्स {person_name}! {hindi_session} के दिन {day_number} की उपस्थिति सफलतापूर्वक दर्ज हो गई है। एस एस पी वन शिविर सफलतापूर्वक पूरा हो गया है। एस एस पी टू शिविर के लिए शुभकामनाएं, धन्यवाद।"
        elif session_type == 'SSP2':
            return f"हैप्पी थॉट्स {person_name}! {hindi_session} के दिन {day_number} की उपस्थिति सफलतापूर्वक दर्ज हो गई है। एस एस पी टू शिविर सफलतापूर्वक पूरा हो गया है। हायर शिविर वन के लिए शुभकामनाएं, धन्यवाद।"
        elif session_type == 'HS1':
            return f"हैप्पी थॉट्स {person_name}! {hindi_session} के दिन {day_number} की उपस्थिति सफलतापूर्वक दर्ज हो गई है। हायर शिविर वन सफलतापूर्वक पूरा हो गया है। हायर शिविर टू के लिए शुभकामनाएं, धन्यवाद।"
        elif session_type == 'HS2':
            return f"हैप्पी थॉट्स {person_name}! {hindi_session} के दिन {day_number} की उपस्थिति सफलतापूर्वक दर्ज हो गई है। हायर शिविर टू सफलतापूर्वक पूरा हो गया है। आपकी आध्यात्मिक यात्रा जारी रहे, धन्यवाद।"
        else:
            return f"हैप्पी थॉट्स {person_name}! {hindi_session} की उपस्थिति सफलतापूर्वक दर्ज हो गई है। धन्यवाद।"
    else:
        # Regular day messages
        return f"हैप्पी थॉट्स {person_name}! {hindi_session} के दिन {day_number} की उपस्थिति सफलतापूर्वक दर्ज हो गई है, धन्यवाद।"

# ================================
# 🚀 NEW ENHANCED ENDPOINTS FOR ADDITIONAL FUNCTIONALITY
# ================================

@csrf_exempt
@require_http_methods(["GET"])
def get_session_progress_api(request, email):
    """Get current session progress for a user"""
    try:
        person = KnownPerson.objects.get(email=email)
        active_session = TejgyanSession.objects.filter(is_active=True).first()
        
        if not active_session:
            return JsonResponse({
                'success': False,
                'error': 'No active session found'
            }, status=404)
        
        session_type = active_session.session_type
        session_duration = get_session_duration(session_type)
        
        if session_type == 'FESTIVAL':
            return JsonResponse({
                'success': True,
                'session_type': session_type,
                'session_name': active_session.session_name,
                'is_festival': True,
                'current_day': 1,
                'total_days': 1,
                'is_completed': False
            })
        
        # Get session-specific progress
        AttendanceModel = get_attendance_model(session_type)
        if AttendanceModel:
            current_attendance = AttendanceModel.objects.filter(
                person=person,
                session_reference=active_session
            ).first()
            
            if current_attendance:
                return JsonResponse({
                    'success': True,
                    'session_type': session_type,
                    'session_name': active_session.session_name,
                    'current_day': current_attendance.day_number,
                    'total_days': session_duration,
                    'is_completed': current_attendance.is_completed,
                    'attendance_date': current_attendance.attendance_date.isoformat()
                })
        
        return JsonResponse({
            'success': True,
            'session_type': session_type,
            'session_name': active_session.session_name,
            'current_day': 0,
            'total_days': session_duration,
            'is_completed': False
        })
        
    except KnownPerson.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Person not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting session progress: {e}")
        return JsonResponse({
            'success': False,
            'error': 'System error occurred'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def check_repeat_eligibility_api(request, email):
    """Check if user is eligible for repeat attendance"""
    try:
        person = KnownPerson.objects.get(email=email)
        active_session = TejgyanSession.objects.filter(is_active=True).first()
        
        if not active_session:
            return JsonResponse({
                'success': False,
                'error': 'No active session found'
            }, status=404)
        
        today = timezone.now().date()
        session_type = active_session.session_type
        
        is_repeat, repeat_info = check_if_repeat_attendance(person, session_type, today, active_session)
        
        if is_repeat:
            return JsonResponse({
                'success': True,
                'is_repeat_eligible': True,
                'days_gap': repeat_info['days_gap'],
                'last_completion_date': repeat_info['last_completion_date'].isoformat(),
                'session_type': session_type
            })
        else:
            return JsonResponse({
                'success': True,
                'is_repeat_eligible': False,
                'session_type': session_type
            })
        
    except KnownPerson.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Person not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error checking repeat eligibility: {e}")
        return JsonResponse({
            'success': False,
            'error': 'System error occurred'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_detailed_user_state_api(request, email):
    """Get comprehensive user state for voice system"""
    try:
        person = KnownPerson.objects.get(email=email)
        active_session = TejgyanSession.objects.filter(is_active=True).first()
        
        if not active_session:
            return JsonResponse({
                'success': False,
                'error': 'No active session found'
            }, status=404)
        
        session_type = active_session.session_type
        voice_message, voice_mode = get_current_state_voice_message(email, person.name, session_type)
        
        # Get renewal status
        can_mark, renewal_state, hours_remaining, last_attendance = check_advanced_attendance_renewal(person, active_session)
        
        # Get user eligibility
        user_shivir_level = person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(person, user_shivir_level)
        
        return JsonResponse({
            'success': True,
            'person_name': person.name,
            'person_email': person.email,
            'is_active': person.is_active,
            'is_blacklisted': person.is_blacklisted,
            'shivir_level': user_shivir_level,
            'eligible_sessions': eligible_sessions,
            'is_eligible_for_current': session_type in eligible_sessions,
            'current_session': {
                'name': active_session.session_name,
                'type': session_type,
                'duration': get_session_duration(session_type)
            },
            'renewal_status': {
                'can_mark': can_mark,
                'state': renewal_state,
                'hours_remaining': hours_remaining,
                'seconds_remaining': int(hours_remaining * 3600) if hours_remaining else 0,
                'last_attendance': last_attendance.timestamp.isoformat() if last_attendance else None
            },
            'voice_system': {
                'message': voice_message,
                'mode': voice_mode,
                'repeat_interval': VOICE_REPEAT_SECONDS,
                'max_repeats': MAX_VOICE_REPEATS if voice_mode != VOICE_MODE_WAIT_NEXT_DAY else -1
            }
        })
        
    except KnownPerson.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Person not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting detailed user state: {e}")
        return JsonResponse({
            'success': False,
            'error': 'System error occurred'
        }, status=500)

# ================================
# 🔄 ENHANCED EXISTING ENDPOINTS
# ================================

@csrf_exempt
@require_http_methods(["POST"])
def mark_attendance_web(request):
    """
    🚀 ENHANCED: Attendance marking with all advanced features integrated
    """
    try:
        # 🚨 DEBUG: Confirm new code is running
        print("🚨 MARK ATTENDANCE WEB API CALLED!")
        print(f"🚨 ATTENDANCE_RENEWAL_HOURS = {ATTENDANCE_RENEWAL_HOURS}")
        
        data = json.loads(request.body or "{}")
        person_email = data.get('email')
        session_type = data.get('session_type', 'MA')

        if not person_email:
            return JsonResponse({
                'success': False,
                'error': 'no_email',
                'message': 'Email is required but not provided'
            }, status=400)

        try:
            person = KnownPerson.objects.get(email=person_email)
        except KnownPerson.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'person_not_found',
                'message': 'Person not found in database'
            }, status=404)

        session = TejgyanSession.objects.filter(is_active=True).first()
        if not session:
            return JsonResponse({
                'success': False,
                'error': 'no_active_session',
                'message': 'No active session available'
            }, status=400)

        if person.is_blacklisted:
            return JsonResponse({
                'success': False,
                'error': 'blacklisted',
                'message': 'This person is blacklisted',
                'hindi_voice_message': get_blacklist_message(person.name),
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            }, status=403)

        if not person.is_active:
            return JsonResponse({
                'success': False,
                'error': 'inactive',
                'message': 'This person is inactive',
                'hindi_voice_message': get_inactive_message(person.name),
                'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
            }, status=403)

        # 🔧 COMPLETELY FIXED: Use advanced flexible cooldown logic
        can_mark, renewal_state, hours_remaining, last_attendance = check_advanced_attendance_renewal(person, session)

        if not can_mark:
            if renewal_state == "just_marked":
                voice_message, voice_mode = get_current_state_voice_message(person.email, person.name, session.session_type)
                return JsonResponse({
                    'success': False,
                    'error': 'just_marked',
                    'message': 'Attendance already marked moments ago',
                    'renewal_info': {
                        'hours_remaining': hours_remaining,
                        'seconds_remaining': int(hours_remaining * 3600),
                        'last_attendance': last_attendance.timestamp.isoformat() if last_attendance else None
                    },
                    'hindi_voice_message': voice_message,
                    'voice_mode': voice_mode
                }, status=409)
            else:
                # 🔧 FIXED: Show appropriate time units based on renewal period
                if ATTENDANCE_RENEWAL_HOURS < 1.0:  # Less than 1 hour
                    if hours_remaining < 0.0167:  # Less than 1 minute
                        seconds_remaining = int(hours_remaining * 3600)
                        wait_msg = f"Please wait {seconds_remaining} seconds"
                    else:
                        minutes_remaining = int(hours_remaining * 60)
                        wait_msg = f"Please wait {minutes_remaining} minutes"
                else:  # 1 hour or more
                    if hours_remaining > 1:
                        wait_msg = f"Please wait {hours_remaining:.1f} hours"
                    else:
                        minutes_remaining = int(hours_remaining * 60)
                        wait_msg = f"Please wait {minutes_remaining} minutes"
                
                return JsonResponse({
                    'success': False,
                    'error': 'cooldown_active',
                    'message': wait_msg,
                    'renewal_info': {
                        'hours_remaining': hours_remaining,
                        'seconds_remaining': int(hours_remaining * 3600),
                        'renewal_config': {
                            'hours': ATTENDANCE_RENEWAL_HOURS,
                            'seconds': int(ATTENDANCE_RENEWAL_HOURS * 3600),
                        },
                        'last_attendance': last_attendance.timestamp.isoformat() if last_attendance else None
                    },
                    'hindi_voice_message': get_mark_next_day_message(person.name, hours_remaining),
                    'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
                }, status=429)

        # Continue with day calculation using enhanced logic
        today = timezone.localdate()
        session_duration = get_session_duration(session.session_type)
        
        # Check for existing session attendance
        AttendanceModel = get_attendance_model(session.session_type)
        current_day = 1
        is_completed = False
        
        if AttendanceModel:
            existing_attendance = AttendanceModel.objects.filter(
                person=person,
                session_reference=session
            ).first()
            
            if existing_attendance:
                current_day = existing_attendance.day_number
                is_completed = existing_attendance.is_completed

        # Prevent double attendance for today
        if Attendance.objects.filter(
            person=person, session=session, timestamp__date=today
        ).exists():
            voice_message, voice_mode = get_current_state_voice_message(person.email, person.name, session.session_type)
            return JsonResponse({
                'success': False,
                'error': 'already_marked_today',
                'message': 'Attendance already marked for today',
                'hindi_voice_message': voice_message,
                'voice_mode': voice_mode
            }, status=409)

        # Create attendance record
        Attendance.objects.create(person=person, session=session, timestamp=timezone.now())

        # Generate enhanced voice message with session and day info
        is_last_day = (current_day == session_duration)
        hindi_message = get_day_attendance_marked_message(
            person.name, session.session_type, current_day, session_duration
        )
        
        try:
            speak(hindi_message)
        except Exception as e:
            logger.warning(f"Voice playback failed: {e}")

        return JsonResponse({
            'success': True,
            'message': f'Attendance marked for day {current_day} of {session.session_type}',
            'person_name': person.name,
            'day_number': current_day,
            'max_days': session_duration,
            'is_last_day': is_last_day,
            'session_completed': is_completed,
            'hindi_voice_message': hindi_message,
            'voice_mode': VOICE_MODE_SUCCESS
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'invalid_json'}, status=400)
    except Exception as e:
        logger.error(f"Error in enhanced mark_attendance_web: {e}", exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': 'system_error',
            'hindi_voice_message': get_system_error_message('उपयोगकर्ता'),
            'voice_mode': VOICE_MODE_WAIT_NEXT_DAY
        }, status=500)

def get_attendance_stats(request):
    """
    Get real-time attendance statistics for dashboard
    """
    try:
        today = timezone.localdate()
        
        stats = {
            'today_total': Attendance.objects.filter(timestamp__date=today).count(),
            'active_session': None,
            'session_attendance': 0
        }
        
        try:
            active_session = TejgyanSession.objects.filter(is_active=True).first()
        except Exception:
            active_session = None
            
        if active_session:
            stats['active_session'] = {
                'name': active_session.session_name,
                'type': active_session.session_type,
                'conducted_by': active_session.conducted_by,
                'duration': get_session_duration(active_session.session_type)
            }
            try:
                stats['session_attendance'] = Attendance.objects.filter(
                    timestamp__date=today
                ).count()
            except Exception:
                stats['session_attendance'] = 0
        
        return JsonResponse({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Error getting attendance stats: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to get stats'})

@csrf_exempt
@require_http_methods(["POST"])
def generate_hindi_voice(request):
    """
    Generate Hindi voice using ElevenLabs API
    """
    try:
        data = json.loads(request.body)
        hindi_text = data.get('text')
        
        if not hindi_text:
            return JsonResponse({'error': 'No text provided'}, status=400)
        
        logger.info(f"🔊 Generating Hindi voice for: {hindi_text}")
        
        try:
            from .voice_helper import speak
            speak(hindi_text)
            return JsonResponse({
                'success': True,
                'message': 'Hindi voice generated successfully'
            })
        except Exception as voice_error:
            logger.error(f"Voice generation failed: {voice_error}")
            return JsonResponse({
                'success': False,
                'error': 'Voice generation failed'
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in generate_hindi_voice: {e}")
        return JsonResponse({'error': str(e)}, status=500)
