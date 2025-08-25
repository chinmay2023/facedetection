# faceapp/api_views.py - ENHANCED WITH HINDI VOICE INTEGRATION
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import KnownPerson, Attendance, TejgyanSession
from django.utils import timezone
import logging

# 🔥 IMPORT HINDI MESSAGES
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

# Set up logging
logger = logging.getLogger(__name__)

@api_view(['POST'])
def mark_attendance(request):
    """
    ENHANCED: Mark attendance API with Hindi voice messages
    Website displays English - Voice speaks Hindi
    """
    try:
        email = request.data.get("email")
        shivir = request.data.get("shivir")
        
        logger.info(f"Attendance request: email={email}, shivir={shivir}")

        if not email or not shivir:
            logger.warning("Missing email or shivir in request")
            return Response({
                "success": False,
                "error": "Email and shivir are required.",  # English for website
                "hindi_voice_message": "कृपया ईमेल और शिविर की जानकारी दें, धन्यवाद।"  # Hindi for voice
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            person = KnownPerson.objects.get(email=email)
            logger.info(f"Found person: {person.name}")
        except KnownPerson.DoesNotExist:
            logger.error(f"Person not found: {email}")
            return Response({
                "success": False,
                "error": "Person not found.",  # English for website
                "hindi_voice_message": get_person_not_found_message()  # Hindi for voice
            }, status=status.HTTP_404_NOT_FOUND)

        # 🔥 CHECK PERSON STATUS WITH HINDI VOICE MESSAGES

        # Check if person is inactive AND blacklisted
        if not person.is_active and person.is_blacklisted:
            logger.warning(f"Person {person.name} is inactive and blacklisted")
            return Response({
                "success": False,
                "error": "Person is inactive and blacklisted.",  # English for website
                "reason": "Account is both inactive and blacklisted",
                "hindi_voice_message": get_inactive_and_blacklisted_message(person.name)  # Hindi for voice
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if person is inactive
        if not person.is_active:
            logger.warning(f"Person {person.name} is inactive")
            return Response({
                "success": False,
                "error": "Attendance cannot be marked for inactive person.",  # English for website
                "reason": getattr(person, 'deactivated_reason', None) or "Person is deactivated",
                "deactivated_since": getattr(person, 'deactivated_date', None),
                "hindi_voice_message": get_inactive_message(person.name)  # Hindi for voice
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if person is blacklisted
        if person.is_blacklisted:
            logger.warning(f"Person {person.name} is blacklisted")
            return Response({
                "success": False,
                "error": "Attendance cannot be marked for blacklisted person.",  # English for website
                "reason": getattr(person, 'blacklisted_reason', None) or "Person is blacklisted",
                "blacklisted_since": getattr(person, 'blacklisted_date', None),
                "hindi_voice_message": get_blacklist_message(person.name)  # Hindi for voice
            }, status=status.HTTP_403_FORBIDDEN)

        # Get current session safely
        try:
            current_session = TejgyanSession.objects.filter(is_active=True).first()
        except Exception as e:
            logger.error(f"Error getting active session: {e}")
            current_session = None

        if not current_session:
            logger.warning("No active session found")
            return Response({
                "success": False,
                "error": "No active session found.",  # English for website
                "hindi_voice_message": get_no_session_message(person.name)  # Hindi for voice
            }, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.now().date()
        
        # Check for existing attendance
        try:
            already_marked = Attendance.objects.filter(
                person=person, 
                timestamp__date=today,
                session=current_session
            ).exists()
        except Exception as e:
            logger.error(f"Error checking existing attendance: {e}")
            already_marked = False

        if not already_marked:
            try:
                # Create attendance record properly
                attendance_data = {
                    'person': person,
                    'timestamp': timezone.now(),
                    'session': current_session
                }
                
                attendance_record = Attendance.objects.create(**attendance_data)
                
                logger.info(f"Attendance marked successfully for {person.name}")
                
                # 🔥 SUCCESS RESPONSE WITH HINDI VOICE
                return Response({
                    "success": True,
                    "message": f"Attendance marked successfully for {person.name}!",  # English for website
                    "session": current_session.session_name,
                    "timestamp": attendance_record.timestamp.isoformat(),
                    "voice_message": f"Welcome {person.name}! Attendance recorded.",  # English fallback
                    "hindi_voice_message": get_attendance_marked_message(person.name, current_session.session_type)  # 🔥 Hindi for voice
                })
                
            except Exception as e:
                logger.error(f"Error creating attendance record: {e}")
                return Response({
                    "success": False,
                    "error": "Failed to create attendance record.",  # English for website
                    "hindi_voice_message": get_system_error_message(person.name)  # Hindi for voice
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.info(f"Attendance already marked for {person.name} today")
            return Response({
                "success": False,
                "error": "Attendance already marked today.",  # English for website
                "info": f"Attendance already marked for {current_session.session_name}.",
                "hindi_voice_message": get_already_marked_message(person.name)  # 🔥 Hindi for voice
            })
            
    except Exception as e:
        logger.error(f"Unexpected error in mark_attendance: {e}")
        return Response({
            "success": False,
            "error": "System error occurred. Please try again.",  # English for website
            "hindi_voice_message": "सिस्टम में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।"  # Hindi for voice
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 🔥 ENHANCED USER MANAGEMENT FUNCTIONS WITH HINDI VOICE

@api_view(['POST'])
def activate_person(request):
    """Activate a person's account with Hindi voice confirmation"""
    email = request.data.get("email")
    
    if not email:
        return Response({
            "success": False,
            "error": "Email is required.",
            "hindi_voice_message": "कृपया ईमेल की जानकारी दें, धन्यवाद।"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        person.is_active = True
        
        # Clear deactivation fields if they exist
        if hasattr(person, 'deactivated_reason'):
            person.deactivated_reason = ""
        if hasattr(person, 'deactivated_date'):
            person.deactivated_date = None
            
        person.save()
        
        logger.info(f"Person {person.name} activated")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been activated.",  # English for website
            "activated_date": timezone.now().isoformat(),
            "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आपका खाता सफलतापूर्वक सक्रिय हो गया है, धन्यवाद।"  # Hindi for voice
        })
    except KnownPerson.DoesNotExist:
        return Response({
            "success": False,
            "error": "Person not found.",
            "hindi_voice_message": get_person_not_found_message()
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def blacklist_person(request):
    """Add a person to blacklist with Hindi voice warning"""
    email = request.data.get("email")
    reason = request.data.get("reason", "Blacklisted via API")
    
    if not email:
        return Response({
            "success": False,
            "error": "Email is required.",
            "hindi_voice_message": "कृपया ईमेल की जानकारी दें, धन्यवाद।"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        person.is_blacklisted = True
        
        # Set blacklist fields if they exist
        if hasattr(person, 'blacklisted_reason'):
            person.blacklisted_reason = reason
        if hasattr(person, 'blacklisted_date'):
            person.blacklisted_date = timezone.now()
            
        person.save()
        
        logger.info(f"Person {person.name} blacklisted: {reason}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been blacklisted.",  # English for website
            "reason": reason,
            "blacklisted_date": timezone.now().isoformat(),
            "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आपको प्रतिबंधित सूची में डाल दिया गया है। कारण: {reason}, धन्यवाद।"  # Hindi for voice
        })
    except KnownPerson.DoesNotExist:
        return Response({
            "success": False,
            "error": "Person not found.",
            "hindi_voice_message": get_person_not_found_message()
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def unblacklist_person(request):
    """Remove a person from blacklist with Hindi voice confirmation"""
    email = request.data.get("email")
    
    if not email:
        return Response({
            "success": False,
            "error": "Email is required.",
            "hindi_voice_message": "कृपया ईमेल की जानकारी दें, धन्यवाद।"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        person.is_blacklisted = False
        
        # Clear blacklist fields if they exist
        if hasattr(person, 'blacklisted_reason'):
            person.blacklisted_reason = ""
        if hasattr(person, 'blacklisted_date'):
            person.blacklisted_date = None
            
        person.save()
        
        logger.info(f"Person {person.name} removed from blacklist")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been removed from blacklist.",  # English for website
            "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आपको प्रतिबंधित सूची से हटा दिया गया है। अब आप उपस्थिति दर्ज करा सकते हैं, धन्यवाद।"  # Hindi for voice
        })
    except KnownPerson.DoesNotExist:
        return Response({
            "success": False,
            "error": "Person not found.",
            "hindi_voice_message": get_person_not_found_message()
        }, status=status.HTTP_404_NOT_FOUND)

# 🔥 KEEP EXISTING FUNCTIONS WITH ENGLISH RESPONSES (for admin use)

@api_view(['POST'])
def deactivate_person(request):
    """Deactivate a person's account"""
    email = request.data.get("email")
    reason = request.data.get("reason", "Deactivated via API")
    
    if not email:
        return Response({
            "success": False,
            "error": "Email is required."
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        person = KnownPerson.objects.get(email=email)
        person.is_active = False
        
        # Set deactivation fields if they exist
        if hasattr(person, 'deactivated_reason'):
            person.deactivated_reason = reason
        if hasattr(person, 'deactivated_date'):
            person.deactivated_date = timezone.now()
            
        person.save()
        
        logger.info(f"Person {person.name} deactivated: {reason}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been deactivated.",
            "reason": reason,
            "deactivated_date": timezone.now().isoformat()
        })
    except KnownPerson.DoesNotExist:
        return Response({
            "success": False,
            "error": "Person not found."
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def activation_status(request, email):
    """Get activation status of a person"""
    try:
        person = KnownPerson.objects.get(email=email)
        return Response({
            "success": True,
            "name": person.name,
            "email": person.email,
            "is_active": person.is_active,
            "deactivated_reason": getattr(person, 'deactivated_reason', None),
            "deactivated_date": getattr(person, 'deactivated_date', None),
            "is_blacklisted": person.is_blacklisted,
            "blacklisted_reason": getattr(person, 'blacklisted_reason', None),
            "blacklisted_date": getattr(person, 'blacklisted_date', None)
        })
    except KnownPerson.DoesNotExist:
        return Response({
            "success": False,
            "error": "Person not found."
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def blacklist_status(request, email):
    """Get blacklist status of a person"""
    try:
        person = KnownPerson.objects.get(email=email)
        return Response({
            "success": True,
            "name": person.name,
            "email": person.email,
            "is_blacklisted": person.is_blacklisted,
            "blacklisted_reason": getattr(person, 'blacklisted_reason', None),
            "blacklisted_date": getattr(person, 'blacklisted_date', None)
        })
    except KnownPerson.DoesNotExist:
        return Response({
            "success": False,
            "error": "Person not found."
        }, status=status.HTTP_404_NOT_FOUND)
