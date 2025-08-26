# faceapp/api_views.py - ENHANCED WITH ALL FACE_RECOGNIZE_LIVE.PY FEATURES INTEGRATED
# 🔧 COMPLETELY FIXED: Day 2 attendance progression bug & flexible renewal time - FINAL VERSION
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import IntegrityError
from datetime import date, timedelta
import logging

# Enhanced model imports
from .models import (
    KnownPerson, Attendance, TejgyanSession,
    MA_Attendance, SSP1_Attendance, SSP2_Attendance, 
    HS1_Attendance, HS2_Attendance,
    MA_Repeaters, SSP1_Repeaters, SSP2_Repeaters, 
    HS1_Repeaters, HS2_Repeaters
)

# Enhanced Hindi messages import
from .hindi_messages import (
    get_attendance_marked_message,
    get_already_marked_message,
    get_blacklist_message,
    get_inactive_message,
    get_inactive_and_blacklisted_message,
    get_no_session_message,
    get_system_error_message,
    get_person_not_found_message
)

# Safe import for voice helper
try:
    from .voice_helper import speak
except ImportError:
    def speak(message):
        print(f"Voice: {message}")

# Set up logging
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
        'MA': MA_Attendance, 
        'SSP1': SSP1_Attendance, 
        'SSP2': SSP2_Attendance,
        'HS1': HS1_Attendance, 
        'HS2': HS2_Attendance,
    }
    return models_map.get(session_type)

def get_repeater_model(session_type):
    """Get the appropriate repeater model for session type"""
    models_map = {
        'MA': MA_Repeaters, 
        'SSP1': SSP1_Repeaters, 
        'SSP2': SSP2_Repeaters,
        'HS1': HS1_Repeaters, 
        'HS2': HS2_Repeaters,
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

def check_session_12_hour_renewal(person, session_type, active_session):
    """🔧 FIXED: Flexible session-specific renewal using configured time"""
    AttendanceModel = get_attendance_model(session_type)
    if AttendanceModel:
        renewal_threshold = timezone.now() - timedelta(hours=ATTENDANCE_RENEWAL_HOURS)
        
        print(f"🔍 SESSION RENEWAL DEBUG for {person.name} ({session_type}):")
        print(f"   Renewal threshold: {renewal_threshold}")
        
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
                
                print(f"   Hours passed: {hours_passed:.4f}")
                print(f"   Hours remaining: {hours_remaining:.4f}")
                
                return False, hours_remaining
        
        print(f"✅ No recent session attendance - can mark")
        return True, 0
    return True, 0

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
# 🔧 NEW: COMPLETION UPDATE FUNCTION
# ================================

def update_person_completion_status(person, session_type):
    """Update KnownPerson shivir field when session is completed"""
    try:
        # Map session types to completion status
        completion_mapping = {
            'MA': 'MA_COMPLETED',
            'SSP1': 'SSP1_COMPLETED', 
            'SSP2': 'SSP2_COMPLETED',
            'HS1': 'HS1_COMPLETED',
            'HS2': 'HS2_COMPLETED'
        }
        
        if session_type in completion_mapping:
            # Update the shivir field to show completion
            current_shivir = person.shivir or ""
            completed_status = completion_mapping[session_type]
            
            # If not already marked as completed
            if completed_status not in current_shivir:
                if current_shivir:
                    person.shivir = f"{current_shivir}, {completed_status}"
                else:
                    person.shivir = completed_status
                
                person.save(update_fields=['shivir'])
                logger.info(f"✅ Updated {person.name}'s shivir field: {person.shivir}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error updating shivir field for {person.name}: {e}")
        return False

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

def get_12_hour_wait_message(name, hours_remaining):
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
# 🚀 ENHANCED MAIN ATTENDANCE API WITH ALL FEATURES - FIXED DAY NUMBERING & FLEXIBLE RENEWAL
# ================================

@api_view(['POST'])
def mark_attendance(request):
    """
    🚀 ENHANCED: Complete attendance API with all face_recognize_live.py features
    🔧 COMPLETELY FIXED: Day 2 attendance progression bug & flexible renewal time - FINAL VERSION
    - Bulletproof renewal system (works with any time interval)
    - FIXED day progression logic for multi-day sessions
    - Session day progression tracking
    - Smart voice repetition system
    - Enhanced user state validation
    """
    try:
        # 🚨 DEBUG: Confirm new fixed code is running
        print("🚨 FIXED ATTENDANCE API CALLED - DAY PROGRESSION BUG RESOLVED!")
        print(f"🚨 ATTENDANCE_RENEWAL_HOURS = {ATTENDANCE_RENEWAL_HOURS}")
        
        email = request.data.get("email")
        shivir = request.data.get("shivir")
        
        logger.info(f"🔒 ENHANCED SECURE: Attendance request - email={email}, shivir={shivir}")

        # Validate required fields
        if not email or not shivir:
            logger.warning("❌ Missing email or shivir in request")
            return Response({
                "success": False,
                "error": "Email and shivir are required.",
                "hindi_voice_message": "कृपया ईमेल और शिविर की जानकारी दें, धन्यवाद।"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find person with proper validation
        try:
            person = KnownPerson.objects.get(email=email)
            logger.info(f"✅ Found person: {person.name}")
        except KnownPerson.DoesNotExist:
            logger.error(f"❌ SECURITY: Person not found - {email}")
            return Response({
                "success": False,
                "error": "Person not found.",
                "hindi_voice_message": get_person_not_found_message()
            }, status=status.HTTP_404_NOT_FOUND)

        # Enhanced person status validation
        if not person.is_active and person.is_blacklisted:
            logger.warning(f"🚫 SECURITY: {person.name} is inactive and blacklisted")
            return Response({
                "success": False,
                "error": "Person is inactive and blacklisted.",
                "reason": "Account is both inactive and blacklisted",
                "security_level": "high_restriction",
                "hindi_voice_message": get_inactive_and_blacklisted_message(person.name),
                "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
            }, status=status.HTTP_403_FORBIDDEN)

        if not person.is_active:
            logger.warning(f"⚠️ SECURITY: {person.name} is inactive")
            return Response({
                "success": False,
                "error": "Attendance cannot be marked for inactive person.",
                "reason": getattr(person, 'deactivated_reason', None) or "Person is deactivated",
                "deactivated_since": getattr(person, 'deactivated_date', None),
                "security_level": "account_inactive",
                "hindi_voice_message": get_inactive_message(person.name),
                "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
            }, status=status.HTTP_403_FORBIDDEN)

        if person.is_blacklisted:
            logger.warning(f"🚫 SECURITY: {person.name} is blacklisted")
            return Response({
                "success": False,
                "error": "Attendance cannot be marked for blacklisted person.",
                "reason": getattr(person, 'blacklisted_reason', None) or "Person is blacklisted",
                "blacklisted_since": getattr(person, 'blacklisted_date', None),
                "security_level": "blacklisted",
                "hindi_voice_message": get_blacklist_message(person.name),
                "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
            }, status=status.HTTP_403_FORBIDDEN)

        # Get current session safely with validation
        try:
            current_session = TejgyanSession.objects.filter(is_active=True).first()
            if current_session:
                logger.info(f"📋 Active session found: {current_session.session_name}")
            else:
                logger.warning("❌ No active session found")
        except Exception as e:
            logger.error(f"❌ CRITICAL: Error getting active session - {e}")
            current_session = None

        if not current_session:
            logger.warning("🚫 SECURITY: No active session available")
            return Response({
                "success": False,
                "error": "No active session found.",
                "security_level": "no_session",
                "hindi_voice_message": get_no_session_message(person.name),
                "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
            }, status=status.HTTP_400_BAD_REQUEST)

        # 🚀 ENHANCED ATTENDANCE LOGIC WITH ALL FEATURES
        today = timezone.now().date()
        current_session_type = current_session.session_type
        
        # Check user eligibility based on shivir background
        user_shivir_level = person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(person, user_shivir_level)
        
        if current_session_type not in eligible_sessions:
            if not user_shivir_level:
                status_msg = "New User - Must Start with MA!"
                voice_message = get_new_user_guidance_message(person.name)
                return Response({
                    "success": False,
                    "error": status_msg,
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
                }, status=status.HTTP_403_FORBIDDEN)
            else:
                status_msg = f"Not Eligible for {current_session_type}!"
                voice_message = get_not_eligible_message(person.name, current_session_type, user_shivir_level)
                return Response({
                    "success": False,
                    "error": status_msg,
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
                }, status=status.HTTP_403_FORBIDDEN)
        
        # 🔧 COMPLETELY FIXED: BULLETPROOF RENEWAL COOLDOWN LOGIC
        can_mark_general, renewal_state, hours_remaining, last_attendance = check_advanced_attendance_renewal(person, current_session)
        
        if not can_mark_general:
            if renewal_state == "just_marked":
                # Just marked moments ago - show already marked message
                voice_message = get_already_marked_message(person.name)
                return Response({
                    "success": False,
                    "error": "Already marked attendance!",
                    "renewal_state": "just_marked",
                    "renewal_info": {
                        "hours_remaining": hours_remaining,
                        "seconds_remaining": int(hours_remaining * 3600),
                        "last_attendance": last_attendance.timestamp.isoformat() if last_attendance else None
                    },
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_ALREADY_MARKED,
                    "last_marked": last_attendance.timestamp.isoformat() if last_attendance else None
                }, status=status.HTTP_409_CONFLICT)
            else:
                # 🔧 FIXED: Show appropriate time units based on renewal period
                if ATTENDANCE_RENEWAL_HOURS < 1.0:  # Less than 1 hour
                    if hours_remaining < 0.0167:  # Less than 1 minute
                        seconds_remaining = int(hours_remaining * 3600)
                        status_msg = f"Please wait {seconds_remaining} seconds before next attendance"
                        voice_message = f"हैप्पी थॉट्स {person.name}, कृपया {seconds_remaining} सेकंड बाद उपस्थिति दर्ज करें।"
                    else:
                        minutes_remaining = int(hours_remaining * 60)
                        status_msg = f"Please wait {minutes_remaining} minutes before next attendance"
                        voice_message = f"हैप्पी थॉट्स {person.name}, कृपया {minutes_remaining} मिनट बाद उपस्थिति दर्ज करें।"
                else:  # 1 hour or more
                    if hours_remaining > 1:
                        status_msg = f"Please wait {hours_remaining:.1f} hours before next attendance"
                    else:
                        minutes_remaining = int(hours_remaining * 60)
                        status_msg = f"Please wait {minutes_remaining} minutes before next attendance"
                    voice_message = get_mark_next_day_message(person.name, hours_remaining)
                
                return Response({
                    "success": False,
                    "error": status_msg,
                    "renewal_state": "in_cooldown",
                    "hours_remaining": hours_remaining,
                    "renewal_config": {
                        "hours": ATTENDANCE_RENEWAL_HOURS,
                        "seconds": int(ATTENDANCE_RENEWAL_HOURS * 3600),
                        "next_allowed": (timezone.now() + timedelta(hours=hours_remaining)).isoformat()
                    },
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # 🚀 CHECK REPEAT ATTENDANCE WITH 1-DAY MINIMUM GAP
        is_repeat, repeat_info = check_if_repeat_attendance(person, current_session_type, today, current_session)
        
        if is_repeat:
            days_gap = repeat_info['days_gap']
            last_completion_date = repeat_info['last_completion_date']
            
            # Check 12-hour renewal for repeat attendance
            can_mark_repeat, repeat_renewal_state, repeat_hours_remaining, _ = check_advanced_attendance_renewal(person, current_session)
            
            if not can_mark_repeat:
                status_msg = f"Repeat attendance - please wait {repeat_hours_remaining:.1f} hours"
                voice_message = get_mark_next_day_message(person.name, repeat_hours_remaining)
                return Response({
                    "success": False,
                    "error": status_msg,
                    "attendance_type": "repeat",
                    "days_gap": days_gap,
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Create repeater record safely
            RepeaterModel = get_repeater_model(current_session_type)
            if RepeaterModel:
                repeater, repeater_created = create_repeater_record_safely(
                    RepeaterModel, person, last_completion_date, days_gap, current_session
                )
                
                if not repeater_created:
                    # Repeater record already exists for today
                    voice_message = get_repeater_already_marked_message(person.name)
                    return Response({
                        "success": False,
                        "error": "Repeat attendance already marked for today!",
                        "attendance_type": "repeat",
                        "days_gap": days_gap,
                        "hindi_voice_message": voice_message,
                        "voice_mode": VOICE_MODE_ALREADY_MARKED
                    }, status=status.HTTP_409_CONFLICT)
            
            # Create general attendance record for repeat
            try:
                Attendance.objects.create(person=person, session=current_session)
                
                voice_message = get_repeater_welcome_message(person.name, days_gap)
                
                return Response({
                    "success": True,
                    "message": f"Repeat Attendance - Welcome Back After {days_gap} Days!",
                    "person_name": person.name,
                    "person_email": person.email,
                    "session": current_session.session_name,
                    "session_type": current_session.session_type,
                    "attendance_type": "repeat",
                    "days_gap": days_gap,
                    "repeat_count": repeater.repeat_count if repeater else 1,
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_SUCCESS,
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_201_CREATED)
                
            except IntegrityError:
                voice_message = get_already_marked_message(person.name)
                return Response({
                    "success": False,
                    "error": f"Already marked for {current_session.get_session_type_display()}!",
                    "attendance_type": "repeat",
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_ALREADY_MARKED
                }, status=status.HTTP_409_CONFLICT)
        
        # 🚀 HANDLE FESTIVAL SESSIONS
        if current_session_type == 'FESTIVAL':
            try:
                Attendance.objects.create(person=person, session=current_session)
                voice_message = get_attendance_marked_message(person.name, current_session_type)
                
                return Response({
                    "success": True,
                    "message": "Festival Attendance Marked!",
                    "person_name": person.name,
                    "person_email": person.email,
                    "session": current_session.session_name,
                    "session_type": current_session.session_type,
                    "attendance_type": "festival",
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_SUCCESS,
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_201_CREATED)
                
            except IntegrityError:
                voice_message = get_already_marked_message(person.name)
                return Response({
                    "success": False,
                    "error": f"Already marked for {current_session.get_session_type_display()}!",
                    "attendance_type": "festival",
                    "hindi_voice_message": voice_message,
                    "voice_mode": VOICE_MODE_ALREADY_MARKED
                }, status=status.HTTP_409_CONFLICT)
        
        # 🚀 HANDLE REGULAR SESSION ATTENDANCE WITH DAY PROGRESSION - COMPLETELY FIXED
        else:
            AttendanceModel = get_attendance_model(current_session_type)
            
            if AttendanceModel:
                # 🔧 CRITICAL FIX: Check existing session attendance for THIS SPECIFIC SESSION
                existing_attendance = AttendanceModel.objects.filter(
                    person=person,
                    session_reference=current_session  # Only check for current session
                ).first()
                
                session_duration = get_session_duration(current_session_type)
                
                if existing_attendance:
                    print(f"🎯 EXISTING ATTENDANCE FOUND for {person.name}")
                    print(f"   Current day: {existing_attendance.day_number}/{session_duration}")
                    print(f"   Is completed: {existing_attendance.is_completed}")
                    
                    # User has existing attendance for THIS SESSION
                    if existing_attendance.is_completed:
                        print(f"❌ SESSION ALREADY COMPLETED")
                        voice_message = get_session_already_completed_message(person.name, current_session_type)
                        return Response({
                            "success": False,
                            "error": "Session Already Completed - Come for Next Session",
                            "attendance_type": "session",
                            "session_completed": True,
                            "hindi_voice_message": voice_message,
                            "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
                        }, status=status.HTTP_409_CONFLICT)
                        
                    elif existing_attendance.day_number < session_duration:
                        # 🔧 CRITICAL FIX: REMOVED THE BROKEN "today's attendance exists" CHECK
                        # OLD BROKEN CODE (REMOVED):
                        # today_attendance_exists = Attendance.objects.filter(
                        #     person=person, 
                        #     session=current_session, 
                        #     timestamp__date=today
                        # ).exists()
                        # if today_attendance_exists:
                        #     return 409 CONFLICT  # This was blocking Day 2!
                        
                        # 🎯 NEW FIXED LOGIC: Only check renewal time, allow day progression
                        print(f"🎯 DAY PROGRESSION: From day {existing_attendance.day_number} to {existing_attendance.day_number + 1}")
                        
                        # Increment day for continuing session
                        existing_attendance.day_number += 1
                        existing_attendance.attendance_date = today
                        
                        if existing_attendance.day_number >= session_duration:
                            existing_attendance.is_completed = True
                            print(f"✅ SESSION COMPLETED at day {existing_attendance.day_number}")
                        
                        existing_attendance.save()
                        
                        # Create general attendance record
                        try:
                            Attendance.objects.create(person=person, session=current_session)
                            print(f"✅ GENERAL ATTENDANCE CREATED for day {existing_attendance.day_number}")
                        except IntegrityError:
                            print(f"⚠️ General attendance already exists, skipping")
                            pass
                        
                        # Handle completion and voice messages
                        if existing_attendance.is_completed:
                            # Update KnownPerson completion status
                            success = update_person_completion_status(person, current_session_type)
                            voice_message = get_day_attendance_marked_message(person.name, current_session_type, existing_attendance.day_number, session_duration)
                            status_msg = f"Session Completed - {current_session.get_session_type_display()}!"
                        else:
                            voice_message = get_day_attendance_marked_message(person.name, current_session_type, existing_attendance.day_number, session_duration)
                            status_msg = f"Day {existing_attendance.day_number}/{session_duration} - {current_session.get_session_type_display()}"
                        
                        print(f"🎉 SUCCESS: {status_msg}")
                        
                        return Response({
                            "success": True,
                            "message": status_msg,
                            "person_name": person.name,
                            "person_email": person.email,
                            "session": current_session.session_name,
                            "session_type": current_session.session_type,
                            "attendance_type": "session",
                            "day_number": existing_attendance.day_number,
                            "total_days": session_duration,
                            "is_completed": existing_attendance.is_completed,
                            "is_last_day": existing_attendance.day_number == session_duration,
                            "hindi_voice_message": voice_message,
                            "voice_mode": VOICE_MODE_SUCCESS,
                            "timestamp": timezone.now().isoformat()
                        }, status=status.HTTP_201_CREATED)
                    
                    else:
                        # Day number >= session_duration but not marked as completed (edge case)
                        print(f"🔧 EDGE CASE: Marking session as completed")
                        existing_attendance.is_completed = True
                        existing_attendance.save()
                        
                        voice_message = get_already_marked_message(person.name)
                        return Response({
                            "success": False,
                            "error": "Session already completed!",
                            "attendance_type": "session",
                            "hindi_voice_message": voice_message,
                            "voice_mode": VOICE_MODE_ALREADY_MARKED
                        }, status=status.HTTP_409_CONFLICT)
                
                else:
                    # 🔧 NEW USER: Create NEW session attendance starting at Day 1
                    print(f"🆕 CREATING NEW ATTENDANCE for {person.name} - Day 1/{session_duration}")
                    try:
                       new_attendance = AttendanceModel.objects.create(
                            person=person,
                            day_number=1,  # ✅ Always start at Day 1 for new session
                            session_reference=current_session,
                            attendance_date=today,
                            is_completed=(session_duration == 1)
                        )
                       print(f"✅ NEW SESSION ATTENDANCE CREATED: Day 1/{session_duration}")

                    except IntegrityError as e:
                        print(f"❌ INTEGRITYERROR: {e}")
                        voice_message = get_already_marked_message(person.name)
                        return Response({
                            "success": False,
                            "error": f"Database constraint violation: {str(e)}",
                            "attendance_type": "session",
                            "hindi_voice_message": voice_message,
                            "voice_mode": VOICE_MODE_ALREADY_MARKED
                        }, status=status.HTTP_409_CONFLICT)
                    
                    # Create general attendance record
                    try:
                        Attendance.objects.create(person=person, session=current_session)
                        print(f"✅ GENERAL ATTENDANCE CREATED for Day 1")
                    except IntegrityError:
                        print(f"⚠️ General attendance already exists")
                        pass
                    
                    # Handle single-day session completion
                    if session_duration == 1:
                        success = update_person_completion_status(person, current_session_type)
                        voice_message = get_day_attendance_marked_message(person.name, current_session_type, 1, session_duration)
                        status_msg = f"Session Completed - {current_session.get_session_type_display()}!"
                    else:
                        voice_message = get_day_attendance_marked_message(person.name, current_session_type, 1, session_duration)
                        status_msg = f"Day 1/{session_duration} - {current_session.get_session_type_display()}"
                    
                    print(f"🎉 NEW USER SUCCESS: {status_msg}")
                    
                    return Response({
                        "success": True,
                        "message": status_msg,
                        "person_name": person.name,
                        "person_email": person.email,
                        "session": current_session.session_name,
                        "session_type": current_session.session_type,
                        "attendance_type": "session",
                        "day_number": 1,
                        "total_days": session_duration,
                        "is_completed": (session_duration == 1),
                        "is_last_day": (session_duration == 1),
                        "hindi_voice_message": voice_message,
                        "voice_mode": VOICE_MODE_SUCCESS,
                        "timestamp": timezone.now().isoformat()
                    }, status=status.HTTP_201_CREATED)
        
        return Response({
            "success": True,
            "message": "Attendance processed successfully",
            "person_name": person.name,
            "hindi_voice_message": get_attendance_marked_message(person.name, current_session_type),
            "voice_mode": VOICE_MODE_SUCCESS
        }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"❌ CRITICAL: Unexpected error in enhanced mark_attendance - {e}")
        return Response({
            "success": False,
            "error": "System error occurred. Please try again.",
            "technical_error": str(e),
            "security_status": "system_failure",
            "hindi_voice_message": "सिस्टम में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।",
            "voice_mode": VOICE_MODE_WAIT_NEXT_DAY
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================
# 🚀 NEW ENHANCED ENDPOINTS FOR ADDITIONAL FUNCTIONALITY
# ================================

@api_view(['GET'])
def get_session_progress(request, email):
    """Get current session progress for a user"""
    try:
        person = KnownPerson.objects.get(email=email)
        active_session = TejgyanSession.objects.filter(is_active=True).first()
        
        if not active_session:
            return Response({
                'success': False,
                'error': 'No active session found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        session_type = active_session.session_type
        session_duration = get_session_duration(session_type)
        
        if session_type == 'FESTIVAL':
            return Response({
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
                return Response({
                    'success': True,
                    'session_type': session_type,
                    'session_name': active_session.session_name,
                    'current_day': current_attendance.day_number,
                    'total_days': session_duration,
                    'is_completed': current_attendance.is_completed,
                    'attendance_date': current_attendance.attendance_date.isoformat()
                })
        
        return Response({
            'success': True,
            'session_type': session_type,
            'session_name': active_session.session_name,
            'current_day': 0,
            'total_days': session_duration,
            'is_completed': False
        })
        
    except KnownPerson.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Person not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting session progress: {e}")
        return Response({
            'success': False,
            'error': 'System error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def check_repeat_eligibility(request, email):
    """Check if user is eligible for repeat attendance"""
    try:
        person = KnownPerson.objects.get(email=email)
        active_session = TejgyanSession.objects.filter(is_active=True).first()
        
        if not active_session:
            return Response({
                'success': False,
                'error': 'No active session found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        today = timezone.now().date()
        session_type = active_session.session_type
        
        is_repeat, repeat_info = check_if_repeat_attendance(person, session_type, today, active_session)
        
        if is_repeat:
            return Response({
                'success': True,
                'is_repeat_eligible': True,
                'days_gap': repeat_info['days_gap'],
                'last_completion_date': repeat_info['last_completion_date'].isoformat(),
                'session_type': session_type
            })
        else:
            return Response({
                'success': True,
                'is_repeat_eligible': False,
                'session_type': session_type
            })
        
    except KnownPerson.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Person not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error checking repeat eligibility: {e}")
        return Response({
            'success': False,
            'error': 'System error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_detailed_user_state(request, email):
    """Get comprehensive user state for voice system"""
    try:
        person = KnownPerson.objects.get(email=email)
        active_session = TejgyanSession.objects.filter(is_active=True).first()
        
        if not active_session:
            return Response({
                'success': False,
                'error': 'No active session found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        session_type = active_session.session_type
        voice_message, voice_mode = get_current_state_voice_message(email, person.name, session_type)
        
        # Get renewal status
        can_mark, renewal_state, hours_remaining, last_attendance = check_advanced_attendance_renewal(person, active_session)
        
        # Get user eligibility
        user_shivir_level = person.get_shivir_background_level()
        eligible_sessions = get_user_eligible_sessions(person, user_shivir_level)
        
        return Response({
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
        return Response({
            'success': False,
            'error': 'Person not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting detailed user state: {e}")
        return Response({
            'success': False,
            'error': 'System error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================================
# 🔥 EXISTING ENHANCED USER MANAGEMENT FUNCTIONS (UNCHANGED)
# ================================

@api_view(['POST'])
def activate_person(request):
    """🔒 SECURITY ENHANCED: Activate a person's account with Hindi voice confirmation"""
    email = request.data.get("email")
    admin_reason = request.data.get("reason", "Activated via API")
    
    if not email:
        logger.warning("❌ Missing email in activation request")
        return Response({
            "success": False,
            "error": "Email is required.",
            "hindi_voice_message": "कृपया ईमेल की जानकारी दें, धन्यवाद।"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        
        if person.is_active:
            logger.info(f"ℹ️ {person.name} is already active")
            return Response({
                "success": False,
                "error": f"{person.name} is already active.",
                "current_status": "already_active",
                "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आपका खाता पहले से ही सक्रिय है, धन्यवाद।"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        person.is_active = True
        if hasattr(person, 'deactivated_reason'):
            person.deactivated_reason = ""
        if hasattr(person, 'deactivated_date'):
            person.deactivated_date = None
        person.save()
        
        logger.info(f"✅ SUCCESS: Person {person.name} activated by admin")
        
        hindi_message = f"हैप्पी थॉट्स {person.name}, आपका खाता सफलतापूर्वक सक्रिय हो गया है, धन्यवाद।"
        try:
            speak(hindi_message)
        except Exception as voice_error:
            logger.warning(f"⚠️ Voice announcement failed: {voice_error}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been activated.",
            "person_name": person.name,
            "person_email": person.email,
            "activated_date": timezone.now().isoformat(),
            "admin_reason": admin_reason,
            "security_status": "account_activated",
            "hindi_voice_message": hindi_message
        }, status=status.HTTP_200_OK)
        
    except KnownPerson.DoesNotExist:
        logger.error(f"❌ SECURITY: Person not found for activation - {email}")
        return Response({
            "success": False,
            "error": "Person not found.",
            "security_status": "person_not_found",
            "hindi_voice_message": get_person_not_found_message()
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error activating person - {e}")
        return Response({
            "success": False,
            "error": "System error during activation.",
            "technical_error": str(e),
            "security_status": "activation_failed",
            "hindi_voice_message": "खाता सक्रिय करने में समस्या है। कृपया एडमिन से संपर्क करें, धन्यवाद।"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def blacklist_person(request):
    """🔒 SECURITY ENHANCED: Add a person to blacklist with Hindi voice warning"""
    email = request.data.get("email")
    reason = request.data.get("reason", "Blacklisted via API")
    admin_user = request.data.get("admin_user", "System Admin")
    
    if not email:
        logger.warning("❌ Missing email in blacklist request")
        return Response({
            "success": False,
            "error": "Email is required.",
            "hindi_voice_message": "कृपया ईमेल की जानकारी दें, धन्यवाद।"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        
        if person.is_blacklisted:
            logger.info(f"ℹ️ {person.name} is already blacklisted")
            return Response({
                "success": False,
                "error": f"{person.name} is already blacklisted.",
                "current_status": "already_blacklisted",
                "existing_reason": getattr(person, 'blacklisted_reason', 'Unknown'),
                "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आप पहले से ही प्रतिबंधित सूची में हैं, धन्यवाद।"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        person.is_blacklisted = True
        if hasattr(person, 'blacklisted_reason'):
            person.blacklisted_reason = reason
        if hasattr(person, 'blacklisted_date'):
            person.blacklisted_date = timezone.now()
        person.save()
        
        logger.info(f"🚫 SECURITY: Person {person.name} blacklisted by {admin_user} - Reason: {reason}")
        
        hindi_message = f"हैप्पी थॉट्स {person.name}, आपको प्रतिबंधित सूची में डाल दिया गया है। कारण: {reason}। कृपया एडमिन से संपर्क करें, धन्यवाद।"
        try:
            speak(hindi_message)
        except Exception as voice_error:
            logger.warning(f"⚠️ Voice announcement failed: {voice_error}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been blacklisted.",
            "person_name": person.name,
            "person_email": person.email,
            "reason": reason,
            "blacklisted_date": timezone.now().isoformat(),
            "admin_user": admin_user,
            "security_status": "account_blacklisted",
            "hindi_voice_message": hindi_message
        }, status=status.HTTP_200_OK)
        
    except KnownPerson.DoesNotExist:
        logger.error(f"❌ SECURITY: Person not found for blacklisting - {email}")
        return Response({
            "success": False,
            "error": "Person not found.",
            "security_status": "person_not_found",
            "hindi_voice_message": get_person_not_found_message()
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error blacklisting person - {e}")
        return Response({
            "success": False,
            "error": "System error during blacklisting.",
            "technical_error": str(e),
            "security_status": "blacklisting_failed",
            "hindi_voice_message": "प्रतिबंधित सूची में डालने में समस्या है। कृपया एडमिन से संपर्क करें, धन्यवाद।"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def unblacklist_person(request):
    """🔒 SECURITY ENHANCED: Remove a person from blacklist with Hindi voice confirmation"""
    email = request.data.get("email")
    admin_reason = request.data.get("reason", "Unblacklisted via API")
    admin_user = request.data.get("admin_user", "System Admin")
    
    if not email:
        logger.warning("❌ Missing email in unblacklist request")
        return Response({
            "success": False,
            "error": "Email is required.",
            "hindi_voice_message": "कृपया ईमेल की जानकारी दें, धन्यवाद।"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        
        if not person.is_blacklisted:
            logger.info(f"ℹ️ {person.name} is not blacklisted")
            return Response({
                "success": False,
                "error": f"{person.name} is not blacklisted.",
                "current_status": "not_blacklisted",
                "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आप प्रतिबंधित सूची में नहीं हैं, धन्यवाद।"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        person.is_blacklisted = False
        if hasattr(person, 'blacklisted_reason'):
            person.blacklisted_reason = ""
        if hasattr(person, 'blacklisted_date'):
            person.blacklisted_date = None
        person.save()
        
        logger.info(f"✅ SUCCESS: Person {person.name} removed from blacklist by {admin_user}")
        
        hindi_message = f"हैप्पी थॉट्स {person.name}, आपको प्रतिबंधित सूची से हटा दिया गया है। अब आप उपस्थिति दर्ज करा सकते हैं, धन्यवाद।"
        try:
            speak(hindi_message)
        except Exception as voice_error:
            logger.warning(f"⚠️ Voice announcement failed: {voice_error}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been removed from blacklist.",
            "person_name": person.name,
            "person_email": person.email,
            "unblacklisted_date": timezone.now().isoformat(),
            "admin_reason": admin_reason,
            "admin_user": admin_user,
            "security_status": "blacklist_removed",
            "hindi_voice_message": hindi_message
        }, status=status.HTTP_200_OK)
        
    except KnownPerson.DoesNotExist:
        logger.error(f"❌ SECURITY: Person not found for unblacklisting - {email}")
        return Response({
            'success': False,
            'error': 'Person not found.',
            'security_status': 'person_not_found',
            'hindi_voice_message': get_person_not_found_message()
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error unblacklisting person - {e}")
        return Response({
            'success': False,
            'error': 'System error during unblacklisting.',
            'technical_error': str(e),
            'security_status': 'unblacklisting_failed',
            'hindi_voice_message': "प्रतिबंधित सूची से हटाने में समस्या है। कृपया एडमिन से संपर्क करें, धन्यवाद।"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def deactivate_person(request):
    """🔒 SECURITY ENHANCED: Deactivate a person's account"""
    email = request.data.get("email")
    reason = request.data.get("reason", "Deactivated via API")
    admin_user = request.data.get("admin_user", "System Admin")
    
    if not email:
        logger.warning("❌ Missing email in deactivation request")
        return Response({
            "success": False,
            "error": "Email is required."
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        
        if not person.is_active:
            logger.info(f"ℹ️ {person.name} is already inactive")
            return Response({
                "success": False,
                "error": f"{person.name} is already inactive.",
                "current_status": "already_inactive",
                "existing_reason": getattr(person, 'deactivated_reason', 'Unknown')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        person.is_active = False
        if hasattr(person, 'deactivated_reason'):
            person.deactivated_reason = reason
        if hasattr(person, 'deactivated_date'):
            person.deactivated_date = timezone.now()
        person.save()
        
        logger.info(f"⚠️ SECURITY: Person {person.name} deactivated by {admin_user} - Reason: {reason}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been deactivated.",
            "person_name": person.name,
            "person_email": person.email,
            "reason": reason,
            "deactivated_date": timezone.now().isoformat(),
            "admin_user": admin_user,
            "security_status": "account_deactivated"
        }, status=status.HTTP_200_OK)
        
    except KnownPerson.DoesNotExist:
        logger.error(f"❌ SECURITY: Person not found for deactivation - {email}")
        return Response({
            "success": False,
            "error": "Person not found.",
            "security_status": "person_not_found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error deactivating person - {e}")
        return Response({
            "success": False,
            "error": "System error during deactivation.",
            "technical_error": str(e),
            "security_status": "deactivation_failed"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def activation_status(request, email):
    """🔒 SECURITY ENHANCED: Get activation status of a person"""
    try:
        person = KnownPerson.objects.get(email=email)
        logger.info(f"📋 Status check for {person.name}")
        
        return Response({
            "success": True,
            "person_info": {
                "name": person.name,
                "email": person.email,
                "is_active": person.is_active,
                "is_blacklisted": person.is_blacklisted,
                "deactivated_reason": getattr(person, 'deactivated_reason', None),
                "deactivated_date": getattr(person, 'deactivated_date', None),
                "blacklisted_reason": getattr(person, 'blacklisted_reason', None),
                "blacklisted_date": getattr(person, 'blacklisted_date', None),
                "account_status": "active" if person.is_active and not person.is_blacklisted 
                                else "inactive" if not person.is_active 
                                else "blacklisted" if person.is_blacklisted 
                                else "restricted"
            },
            "security_status": "status_retrieved",
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except KnownPerson.DoesNotExist:
        logger.error(f"❌ SECURITY: Person not found for status check - {email}")
        return Response({
            "success": False,
            "error": "Person not found.",
            "security_status": "person_not_found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error getting activation status - {e}")
        return Response({
            "success": False,
            "error": "System error getting status.",
            "technical_error": str(e),
            "security_status": "status_check_failed"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def blacklist_status(request, email):
    """🔒 SECURITY ENHANCED: Get blacklist status of a person"""
    try:
        person = KnownPerson.objects.get(email=email)
        logger.info(f"📋 Blacklist status check for {person.name}")
        
        return Response({
            "success": True,
            "blacklist_info": {
                "name": person.name,
                "email": person.email,
                "is_blacklisted": person.is_blacklisted,
                "blacklisted_reason": getattr(person, 'blacklisted_reason', None),
                "blacklisted_date": getattr(person, 'blacklisted_date', None),
                "blacklist_status": "blacklisted" if person.is_blacklisted else "not_blacklisted"
            },
            "security_status": "blacklist_status_retrieved",
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except KnownPerson.DoesNotExist:
        logger.error(f"❌ SECURITY: Person not found for blacklist status - {email}")
        return Response({
            "success": False,
            "error": "Person not found.",
            "security_status": "person_not_found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error getting blacklist status - {e}")
        return Response({
            "success": False,
            "error": "System error getting blacklist status.",
            "technical_error": str(e),
            "security_status": "blacklist_check_failed"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def attendance_audit(request):
    """🔒 NEW: Get attendance audit information for security monitoring"""
    try:
        today = timezone.now().date()
        
        today_attendance = Attendance.objects.filter(timestamp__date=today)
        
        audit_data = {
            "success": True,
            "audit_info": {
                "date": today.isoformat(),
                "total_attendance_today": today_attendance.count(),
                "unique_persons_today": today_attendance.values('person').distinct().count(),
                "active_sessions": TejgyanSession.objects.filter(is_active=True).count(),
                "total_active_users": KnownPerson.objects.filter(is_active=True, is_blacklisted=False).count(),
                "total_inactive_users": KnownPerson.objects.filter(is_active=False).count(),
                "total_blacklisted_users": KnownPerson.objects.filter(is_blacklisted=True).count(),
            },
            "security_status": "audit_completed",
            "timestamp": timezone.now().isoformat()
        }
        
        logger.info(f"📊 SECURITY AUDIT: Attendance audit completed")
        return Response(audit_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error in attendance audit - {e}")
        return Response({
            "success": False,
            "error": "System error during audit.",
            "technical_error": str(e),
            "security_status": "audit_failed"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
