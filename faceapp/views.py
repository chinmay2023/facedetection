# faceapp/views.py - FIXED: 12-hour renewal + Day-specific Hindi TTS
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
import json
import base64
import io
import numpy as np
from PIL import Image
import face_recognition
import logging
from datetime import timedelta

from .models import (
    KnownPerson, TejgyanSession, Attendance,
    MA_Attendance, SSP1_Attendance, SSP2_Attendance, 
    HS1_Attendance, HS2_Attendance
)

from .hindi_messages import (
    get_person_not_found_message,
    get_blacklist_message,
    get_inactive_message,
    get_inactive_and_blacklisted_message,
    get_no_session_message,
    get_system_error_message
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
    Face recognition API with Hindi voice messages
    """
    try:
        logger.info("Face recognition API called")
        
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            logger.warning("No image data provided")
            return JsonResponse({
                'success': False,
                'error_type': 'no_image',
                'message': 'No image data provided',
                'hindi_voice_message': 'कृपया अपनी तस्वीर प्रदान करें, धन्यवाद।'
            })
        
        face_encoding = process_webcam_image(image_data)
        
        if face_encoding is None:
            logger.info("No face detected in image")
            return JsonResponse({
                'success': False,
                'error_type': 'face_not_found',
                'message': 'No face detected in image',
                'hindi_voice_message': 'कृपया अपना चेहरा कैमरे के सामने स्पष्ट रूप से दिखाएं, धन्यवाद।'
            })
        
        recognized_person = find_matching_person(face_encoding)
        
        if not recognized_person:
            logger.info("🔒 SECURITY: Face not recognized - Unknown person detected")
            return JsonResponse({
                'success': False,
                'error_type': 'person_not_recognized',
                'message': 'Face not recognized. Please register first.',
                'hindi_voice_message': get_person_not_found_message()
            })
        
        logger.info(f"Person recognized: {recognized_person.name}")
        
        # Check person status
        if not recognized_person.is_active and recognized_person.is_blacklisted:
            logger.warning(f"Person {recognized_person.name} is inactive and blacklisted")
            return JsonResponse({
                'success': False,
                'error_type': 'person_inactive_blacklisted',
                'message': 'Account is inactive and blacklisted. Contact administrator.',
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_inactive_and_blacklisted_message(recognized_person.name)
            })
        
        if not recognized_person.is_active:
            logger.warning(f"Person {recognized_person.name} is inactive")
            return JsonResponse({
                'success': False,
                'error_type': 'person_inactive',
                'message': 'Account inactive. Contact administrator.',
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_inactive_message(recognized_person.name)
            })
        
        if recognized_person.is_blacklisted:
            logger.warning(f"Person {recognized_person.name} is blacklisted")
            return JsonResponse({
                'success': False,
                'error_type': 'person_blacklisted',
                'message': 'Access denied. Contact administrator.',
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_blacklist_message(recognized_person.name)
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
                'hindi_voice_message': get_no_session_message(recognized_person.name)
            })
        
        user_data = get_user_display_data(recognized_person, active_session)
        
        logger.info(f"Successfully recognized {recognized_person.name}")
        
        return JsonResponse({
            'success': True,
            'user_data': user_data,
            'session_info': {
                'id': active_session.id,
                'name': active_session.session_name,
                'type': active_session.session_type,
                'conducted_by': active_session.conducted_by
            },
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {e}")
        return JsonResponse({
            'success': False,
            'error_type': 'invalid_data',
            'message': 'Invalid JSON data',
            'hindi_voice_message': 'डेटा में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।'
        })
    except Exception as e:
        logger.error(f"Error in recognize_face_api: {e}")
        return JsonResponse({
            'success': False,
            'error_type': 'system_error',
            'message': 'System error occurred. Please try again.',
            'hindi_voice_message': get_system_error_message('उपयोगकर्ता')
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
        'MA': 5,
        'SSP1': 2,
        'SSP2': 2,
        'HS1': 2,
        'HS2': 2,
        'FESTIVAL': 1
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

@csrf_exempt
@require_http_methods(["POST"])
def mark_attendance_web(request):
    """
    FIXED: Enhanced attendance marking with proper 12-hour renewal and day-specific Hindi TTS
    """
    try:
        data = json.loads(request.body)
        person_email = data.get('email')
        session_type = data.get('session_type', 'MA')
        
        if not person_email:
            return JsonResponse({
                'success': False,
                'error': 'Email required'
            }, status=400)
        
        try:
            person = KnownPerson.objects.get(email=person_email)
        except KnownPerson.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Person not found'
            }, status=404)
        
        session = TejgyanSession.objects.filter(is_active=True).first()
        if not session:
            return JsonResponse({
                'success': False,
                'error': 'No active session'
            }, status=400)
        
        if person.is_blacklisted:
            return JsonResponse({
                'success': False,
                'error': 'Blacklisted'
            }, status=403)
        
        if not person.is_active:
            return JsonResponse({
                'success': False,
                'error': 'Inactive'
            }, status=403)
        
        # FIXED: Proper 12-hour renewal check
        cooldown_hours = getattr(settings, "ATTENDANCE_COOLDOWN", 12)
    
        # Get all attendance records for this person and session, ordered by timestamp
        past_attendance = Attendance.objects.filter(
            person=person, 
            session=session
        ).order_by('timestamp')
        
        # Check if 12-hour cooldown period has passed since last attendance
        if past_attendance.exists():
            last_attendance = past_attendance.last()
            time_since_last = timezone.now() - last_attendance.timestamp
            hours_since_last = time_since_last.total_seconds() / 3600
            
            logger.info(f"Hours since last attendance: {hours_since_last:.2f}")
            
            if hours_since_last < cooldown_hours:
                remaining_hours = cooldown_hours - hours_since_last
                remaining_minutes = int(remaining_hours * 60)
                return JsonResponse({
                    'success': False,
                    'error': 'cooldown_active',
                    'message': f'Please wait {remaining_minutes} more minutes',
                    'wait_minutes': remaining_minutes
                }, status=429)
        
        # Calculate the day number for this attendance
        day_number = past_attendance.count() + 1
        max_days = get_session_max_days(session.session_type)
        
        logger.info(f"Day number: {day_number}, Max days: {max_days}")
        
        # Check if session is already completed
        if day_number > max_days:
            return JsonResponse({
                'success': False,
                'error': 'session_completed',
                'message': f'{session.session_type} session already completed'
            }, status=409)
        
        # Check if attendance already marked for today (additional safety check)
        today = timezone.localdate()
        today_attendance = Attendance.objects.filter(
            person=person,
            session=session,
            timestamp__date=today
        ).exists()
        
        if today_attendance:
            return JsonResponse({
                'success': False,
                'error': 'already_marked_today',
                'message': 'Attendance already marked for today'
            }, status=409)
        
        # Create attendance record
        attendance = Attendance.objects.create(
            person=person,
            session=session,
            timestamp=timezone.now()
        )
        
        # Generate day-specific Hindi TTS message
        is_last_day = (day_number == max_days)
        hindi_message = generate_hindi_attendance_message(
            person.name, 
            session.session_type, 
            day_number, 
            is_last_day
        )
        
        # Play Hindi voice message
        try:
            speak(hindi_message)
        except Exception as voice_error:
            logger.warning(f"Voice announcement failed: {voice_error}")
        
        logger.info(f"Attendance marked successfully for {person.name}, Day {day_number}/{max_days}")
        
        return JsonResponse({
            'success': True,
            'message': f'Attendance marked for day {day_number} of {session.session_type}',
            'day_number': day_number,
            'max_days': max_days,
            'is_last_day': is_last_day,
            'voice_message': hindi_message,
            'session_completed': is_last_day
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in attendance request: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in mark_attendance_web: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'System error occurred'
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
                'conducted_by': active_session.conducted_by
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
