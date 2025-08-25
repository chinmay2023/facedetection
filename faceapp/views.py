# faceapp/views.py - ENHANCED WITH COMPLETE HINDI VOICE INTEGRATION
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

# Import your existing models and utilities
from .models import (
    KnownPerson, TejgyanSession, Attendance,
    MA_Attendance, SSP1_Attendance, SSP2_Attendance, 
    HS1_Attendance, HS2_Attendance
)

# 🔥 IMPORT HINDI MESSAGES
from .hindi_messages import (
    get_person_not_found_message,
    get_blacklist_message,
    get_inactive_message,
    get_inactive_and_blacklisted_message,
    get_no_session_message,
    get_system_error_message
)

# Safe imports with fallbacks
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

# Set up logging
logger = logging.getLogger(__name__)

def attendance_interface(request):
    """
    Render the main face recognition attendance interface
    This displays the beautiful UI with webcam and form
    """
    try:
        # Get active session safely
        try:
            active_session = TejgyanSession.objects.filter(is_active=True).first()
        except Exception:
            active_session = None
        
        # Get today's attendance count safely
        today = timezone.now().date()
        try:
            today_attendance_count = Attendance.objects.filter(
                timestamp__date=today
            ).count()
        except Exception:
            today_attendance_count = 0
        
        # Get total active users safely
        try:
            active_users_count = KnownPerson.objects.filter(
                is_active=True,
                is_blacklisted=False
            ).count()
        except Exception:
            active_users_count = 0
        
        context = {
            'active_session': active_session,
            'session_name': active_session.session_name if active_session else 'No Active Session',
            'session_type': active_session.session_type if active_session else 'None',
            'conducted_by': active_session.conducted_by if active_session else 'Unknown',
            'today_attendance': today_attendance_count,
            'active_users': active_users_count,
            'current_date': today.strftime('%B %d, %Y'),
        }
        
        logger.info("Rendering attendance interface successfully")
        return render(request, 'faceapp/attendance.html', context)
        
    except Exception as e:
        logger.error(f"Error in attendance_interface: {e}")
        # Return basic context if error occurs
        context = {
            'active_session': None,
            'session_name': 'System Error',
            'session_type': 'None',
            'conducted_by': 'System',
            'today_attendance': 0,
            'active_users': 0,
            'current_date': timezone.now().strftime('%B %d, %Y'),
            'error_message': 'Please contact administrator'
        }
        return render(request, 'faceapp/attendance.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def recognize_face_api(request):
    """
    🔥 ENHANCED: Face recognition API with Hindi voice messages
    Website displays English - Voice speaks Hindi
    """
    try:
        logger.info("Face recognition API called")
        
        # Parse the incoming JSON data
        data = json.loads(request.body)
        image_data = data.get('image')
        
        if not image_data:
            logger.warning("No image data provided")
            return JsonResponse({
                'success': False,
                'error_type': 'no_image',
                'message': 'No image data provided',  # English for website
                'hindi_voice_message': 'कृपया अपनी तस्वीर प्रदान करें, धन्यवाद।'  # Hindi for voice
            })
        
        # Process the base64 image
        face_encoding = process_webcam_image(image_data)
        
        if face_encoding is None:
            logger.info("No face detected in image")
            return JsonResponse({
                'success': False,
                'error_type': 'face_not_found',
                'message': 'No face detected in image',  # English for website
                'hindi_voice_message': 'कृपया अपना चेहरा कैमरे के सामने स्पष्ट रूप से दिखाएं, धन्यवाद।'  # Hindi for voice
            })
        
        # Find matching person in database
        recognized_person = find_matching_person(face_encoding)
        
        if not recognized_person:
            logger.info("Face not recognized")
            return JsonResponse({
                'success': False,
                'error_type': 'person_not_recognized',
                'message': 'Face not recognized. Please register first.',  # English for website
                'hindi_voice_message': get_person_not_found_message()  # 🔥 Hindi for voice
            })
        
        logger.info(f"Person recognized: {recognized_person.name}")
        
        # 🔥 CHECK PERSON STATUS WITH HINDI VOICE MESSAGES
        
        # Check if person is inactive AND blacklisted
        if not recognized_person.is_active and recognized_person.is_blacklisted:
            logger.warning(f"Person {recognized_person.name} is inactive and blacklisted")
            return JsonResponse({
                'success': False,
                'error_type': 'person_inactive_blacklisted',
                'message': 'Account is inactive and blacklisted. Contact administrator.',  # English for website
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_inactive_and_blacklisted_message(recognized_person.name)  # 🔥 Hindi for voice
            })
        
        # Check if person is inactive
        if not recognized_person.is_active:
            logger.warning(f"Person {recognized_person.name} is inactive")
            return JsonResponse({
                'success': False,
                'error_type': 'person_inactive',
                'message': 'Account inactive. Contact administrator.',  # English for website
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_inactive_message(recognized_person.name)  # 🔥 Hindi for voice
            })
        
        # Check if person is blacklisted
        if recognized_person.is_blacklisted:
            logger.warning(f"Person {recognized_person.name} is blacklisted")
            return JsonResponse({
                'success': False,
                'error_type': 'person_blacklisted',
                'message': 'Access denied. Contact administrator.',  # English for website
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_blacklist_message(recognized_person.name)  # 🔥 Hindi for voice
            })
        
        # Get active session safely
        try:
            active_session = TejgyanSession.objects.filter(is_active=True).first()
        except Exception:
            active_session = None
            
        if not active_session:
            logger.warning("No active session found")
            return JsonResponse({
                'success': False,
                'error_type': 'no_active_session',
                'message': 'No active session found. Contact administrator.',  # English for website
                'user_data': get_user_display_data(recognized_person),
                'hindi_voice_message': get_no_session_message(recognized_person.name)  # 🔥 Hindi for voice
            })
        
        # 🎉 ALL CHECKS PASSED - RETURN SUCCESS WITH USER DATA
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
            # 🔥 NO HINDI MESSAGE FOR SUCCESS - Will be handled by attendance API
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {e}")
        return JsonResponse({
            'success': False,
            'error_type': 'invalid_data',
            'message': 'Invalid JSON data',  # English for website
            'hindi_voice_message': 'डेटा में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।'  # Hindi for voice
        })
    except Exception as e:
        logger.error(f"Error in recognize_face_api: {e}")
        return JsonResponse({
            'success': False,
            'error_type': 'system_error',
            'message': 'System error occurred. Please try again.',  # English for website
            'hindi_voice_message': get_system_error_message('उपयोगकर्ता')  # 🔥 Hindi for voice (generic user)
        })

def process_webcam_image(image_data):
    """
    Process base64 image data from webcam and extract face encoding
    """
    try:
        logger.info("Processing webcam image")
        
        # Remove data URL prefix if present
        if 'data:image' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert PIL image to numpy array for face_recognition
        image_array = np.array(image)
        
        # Get face encodings using face_recognition
        face_encodings = face_recognition.face_encodings(image_array)
        
        if face_encodings:
            logger.info(f"Found {len(face_encodings)} face(s) in image")
            return face_encodings[0]  # Return first face found
        else:
            logger.info("No faces found in image")
            return None
            
    except Exception as e:
        logger.error(f"Error processing webcam image: {e}")
        return None

def find_matching_person(face_encoding, tolerance=0.8):
    """
    Find matching person in database using face encoding comparison
    FIXED VERSION - Resolves distance calculation bug and improves logging
    """
    try:
        logger.info("🔍 Searching for matching person in database")
        
        # Get all active users with face encodings
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
                
                # Convert stored binary encoding back to numpy array
                try:
                    stored_encoding = np.frombuffer(person.encoding, dtype=np.float64)
                    logger.info(f"📊 Loaded encoding for {person.name}: {len(stored_encoding)} features")
                except Exception as encoding_error:
                    logger.error(f"❌ Failed to load encoding for {person.name}: {encoding_error}")
                    continue
                
                # Calculate face distance (lower = more similar)
                try:
                    distances = face_recognition.face_distance([stored_encoding], face_encoding)
                    distance = distances[0]  # Extract single distance value
                    
                    logger.info(f"📏 Distance for {person.name}: {distance:.4f} (tolerance: {tolerance})")
                    
                    # Check if this is a match
                    if distance <= tolerance:
                        logger.info(f"✅ POTENTIAL MATCH: {person.name} (distance: {distance:.4f})")
                        
                        # Keep track of best match (lowest distance)
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
        
        # Return the best match if found
        if best_match:
            logger.info(f"🎉 FINAL MATCH FOUND: {best_match.name} (distance: {best_distance:.4f})")
            return best_match
        else:
            logger.info(f"❌ No matching person found (tried {known_persons.count()} persons)")
            logger.info(f"📊 Tolerance used: {tolerance} (try increasing to 0.9 if needed)")
            return None
        
    except Exception as e:
        logger.error(f"❌ Critical error in find_matching_person: {e}")
        return None

def get_user_display_data(person, session=None):
    """
    Get user data for display in the form - Safe version without problematic method calls
    """
    try:
        # Get spiritual level safely
        try:
            spiritual_level = getattr(person, 'shivir', None) or 'New User'
        except:
            spiritual_level = 'New User'
        
        # Get current session info if provided
        session_info = 'No Active Session'
        if session:
            session_info = f"{session.session_name} ({session.session_type})"
        
        # Determine status safely
        if not person.is_active:
            reason = getattr(person, 'deactivated_reason', None)
            status = f"❌ Inactive" + (f" - {reason}" if reason else "")
        elif person.is_blacklisted:
            reason = getattr(person, 'blacklisted_reason', None)
            status = f"🚫 Blacklisted" + (f" - {reason}" if reason else "")
        else:
            status = "✅ Active Member"
        
        # Return clean data that matches JavaScript expectations
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

@csrf_exempt
@require_http_methods(["POST"])
def mark_attendance_web(request):
    """
    SIMPLIFIED: Enhanced attendance marking for web interface
    This works with your existing attendance system
    """
    try:
        data = json.loads(request.body)
        person_email = data.get('email')
        session_type = data.get('session_type', 'MA')  # Default to MA
        
        if not person_email:
            return JsonResponse({
                'success': False,
                'error': 'Email required'
            })
        
        # Get person
        try:
            person = KnownPerson.objects.get(email=person_email)
        except KnownPerson.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Person not found'
            })
        
        logger.info(f"Attempting to mark attendance for {person.name}")
        
        # Try to call your existing attendance API
        try:
            from .api_views import mark_attendance
            
            # Create a mock request object for the existing API
            class MockRequest:
                def __init__(self, data):
                    self.data = data
            
            mock_request = MockRequest({
                'email': person_email,
                'shivir': session_type
            })
            
            # Call your existing attendance marking function
            response = mark_attendance(mock_request)
            
            # Process the response
            if hasattr(response, 'content'):
                response_data = json.loads(response.content.decode())
            else:
                response_data = response
            
            # Add voice announcement
            if response_data.get('success'):
                voice_message = f"Welcome {person.name}! Attendance recorded successfully."
                
                # Trigger voice announcement
                try:
                    speak(voice_message)
                except Exception as e:
                    logger.warning(f"Voice announcement failed: {e}")
                
                response_data['voice_message'] = voice_message
                logger.info(f"Attendance marked successfully for {person.name}")
            else:
                logger.warning(f"Attendance marking failed for {person.name}: {response_data.get('error', 'Unknown error')}")
            
            return JsonResponse(response_data)
            
        except ImportError:
            # If api_views doesn't exist, create basic attendance record
            logger.warning("api_views.mark_attendance not found, creating basic record")
            
            # Create basic attendance record
            today = timezone.now().date()
            attendance, created = Attendance.objects.get_or_create(
                person=person,
                timestamp__date=today,
                defaults={'timestamp': timezone.now()}
            )
            
            if created:
                voice_message = f"Welcome {person.name}! Attendance recorded."
                try:
                    speak(voice_message)
                except Exception:
                    pass
                
                return JsonResponse({
                    'success': True,
                    'message': f'Attendance marked for {person.name}',
                    'voice_message': voice_message
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Attendance already marked today'
                })
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in attendance request: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        logger.error(f"Error in mark_attendance_web: {e}")
        return JsonResponse({
            'success': False,
            'error': 'System error occurred'
        })

def get_attendance_stats(request):
    """
    Get real-time attendance statistics for dashboard
    """
    try:
        today = timezone.now().date()
        
        stats = {
            'today_total': Attendance.objects.filter(timestamp__date=today).count(),
            'active_session': None,
            'session_attendance': 0
        }
        
        # Get active session safely
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

# 🔥 ENHANCED: ElevenLabs Hindi voice generation endpoint
@csrf_exempt
@require_http_methods(["POST"])
def generate_hindi_voice(request):
    """
    Generate Hindi voice using ElevenLabs API - Enhanced version
    """
    try:
        data = json.loads(request.body)
        hindi_text = data.get('text')
        
        if not hindi_text:
            return JsonResponse({'error': 'No text provided'}, status=400)
        
        logger.info(f"🔊 Generating Hindi voice for: {hindi_text}")
        
        # Use your existing voice_helper.py with Hindi text
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
