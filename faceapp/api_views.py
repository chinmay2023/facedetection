# faceapp/api_views.py - SECURITY ENHANCED WITH HINDI VOICE INTEGRATION
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

# Safe import for voice helper
try:
    from .voice_helper import speak
except ImportError:
    def speak(message):
        print(f"Voice: {message}")

# Set up logging
logger = logging.getLogger(__name__)

@api_view(['POST'])
def mark_attendance(request):
    """
    🔒 SECURITY ENHANCED: Mark attendance API with Hindi voice messages
    Website displays English - Voice speaks Hindi
    Compatible with unknown person detection security fix
    """
    try:
        email = request.data.get("email")
        shivir = request.data.get("shivir")
        
        logger.info(f"🔒 SECURE: Attendance request - email={email}, shivir={shivir}")

        # Validate required fields
        if not email or not shivir:
            logger.warning("❌ Missing email or shivir in request")
            return Response({
                "success": False,
                "error": "Email and shivir are required.",  # English for website
                "hindi_voice_message": "कृपया ईमेल और शिविर की जानकारी दें, धन्यवाद।"  # Hindi for voice
            }, status=status.HTTP_400_BAD_REQUEST)

        # 🔒 SECURITY: Find person with proper validation
        try:
            person = KnownPerson.objects.get(email=email)
            logger.info(f"✅ Found person: {person.name}")
        except KnownPerson.DoesNotExist:
            logger.error(f"❌ SECURITY: Person not found - {email}")
            return Response({
                "success": False,
                "error": "Person not found.",  # English for website
                "hindi_voice_message": get_person_not_found_message()  # Hindi for voice
            }, status=status.HTTP_404_NOT_FOUND)

        # 🔒 SECURITY: Enhanced person status validation with Hindi voice messages

        # Check if person is inactive AND blacklisted (most restrictive)
        if not person.is_active and person.is_blacklisted:
            logger.warning(f"🚫 SECURITY: {person.name} is inactive and blacklisted")
            return Response({
                "success": False,
                "error": "Person is inactive and blacklisted.",  # English for website
                "reason": "Account is both inactive and blacklisted",
                "security_level": "high_restriction",
                "hindi_voice_message": get_inactive_and_blacklisted_message(person.name)  # Hindi for voice
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if person is inactive
        if not person.is_active:
            logger.warning(f"⚠️ SECURITY: {person.name} is inactive")
            return Response({
                "success": False,
                "error": "Attendance cannot be marked for inactive person.",  # English for website
                "reason": getattr(person, 'deactivated_reason', None) or "Person is deactivated",
                "deactivated_since": getattr(person, 'deactivated_date', None),
                "security_level": "account_inactive",
                "hindi_voice_message": get_inactive_message(person.name)  # Hindi for voice
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if person is blacklisted
        if person.is_blacklisted:
            logger.warning(f"🚫 SECURITY: {person.name} is blacklisted")
            return Response({
                "success": False,
                "error": "Attendance cannot be marked for blacklisted person.",  # English for website
                "reason": getattr(person, 'blacklisted_reason', None) or "Person is blacklisted",
                "blacklisted_since": getattr(person, 'blacklisted_date', None),
                "security_level": "blacklisted",
                "hindi_voice_message": get_blacklist_message(person.name)  # Hindi for voice
            }, status=status.HTTP_403_FORBIDDEN)

        # 🔒 SECURITY: Get current session safely with validation
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
                "error": "No active session found.",  # English for website
                "security_level": "no_session",
                "hindi_voice_message": get_no_session_message(person.name)  # Hindi for voice
            }, status=status.HTTP_400_BAD_REQUEST)

        # 🔒 SECURITY: Enhanced duplicate attendance check
        today = timezone.now().date()
        
        try:
            existing_attendance = Attendance.objects.filter(
                person=person, 
                timestamp__date=today,
                session=current_session
            ).first()
            
            if existing_attendance:
                logger.info(f"ℹ️ DUPLICATE: Attendance already exists for {person.name}")
                already_marked = True
                existing_time = existing_attendance.timestamp
            else:
                already_marked = False
                existing_time = None
                
        except Exception as e:
            logger.error(f"❌ CRITICAL: Error checking existing attendance - {e}")
            already_marked = False
            existing_time = None

        # 🎉 MARK ATTENDANCE OR HANDLE DUPLICATE
        if not already_marked:
            try:
                # 🔒 SECURITY: Create attendance record with full validation
                attendance_data = {
                    'person': person,
                    'timestamp': timezone.now(),
                    'session': current_session
                }
                
                # Create the attendance record
                attendance_record = Attendance.objects.create(**attendance_data)
                
                logger.info(f"✅ SUCCESS: Attendance marked for {person.name} in {current_session.session_name}")
                
                # 🔥 SUCCESS RESPONSE WITH HINDI VOICE
                success_response = {
                    "success": True,
                    "message": f"Attendance marked successfully for {person.name}!",  # English for website
                    "person_name": person.name,
                    "person_email": person.email,
                    "session": current_session.session_name,
                    "session_type": current_session.session_type,
                    "timestamp": attendance_record.timestamp.isoformat(),
                    "attendance_id": attendance_record.id,
                    "security_status": "verified",
                    "voice_message": f"Welcome {person.name}! Attendance recorded.",  # English fallback
                    "hindi_voice_message": get_attendance_marked_message(person.name, current_session.session_type)  # 🔥 Hindi for voice
                }
                
                # 🎵 Trigger Hindi voice announcement
                try:
                    hindi_message = get_attendance_marked_message(person.name, current_session.session_type)
                    speak(hindi_message)
                    logger.info(f"🔊 Hindi voice announcement triggered for {person.name}")
                except Exception as voice_error:
                    logger.warning(f"⚠️ Voice announcement failed: {voice_error}")
                
                return Response(success_response, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"❌ CRITICAL: Failed to create attendance record for {person.name} - {e}")
                return Response({
                    "success": False,
                    "error": "Failed to create attendance record.",  # English for website
                    "technical_error": str(e),
                    "security_status": "system_error",
                    "hindi_voice_message": get_system_error_message(person.name)  # Hindi for voice
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Handle duplicate attendance
            logger.info(f"ℹ️ DUPLICATE: Attendance already marked for {person.name} today")
            return Response({
                "success": False,
                "error": "Attendance already marked today.",  # English for website
                "info": f"Attendance already marked for {current_session.session_name}.",
                "existing_timestamp": existing_time.isoformat() if existing_time else None,
                "session": current_session.session_name,
                "session_type": current_session.session_type,
                "security_status": "duplicate_attempt",
                "hindi_voice_message": get_already_marked_message(person.name)  # 🔥 Hindi for voice
            }, status=status.HTTP_409_CONFLICT)
            
    except Exception as e:
        logger.error(f"❌ CRITICAL: Unexpected error in mark_attendance - {e}")
        return Response({
            "success": False,
            "error": "System error occurred. Please try again.",  # English for website
            "technical_error": str(e),
            "security_status": "system_failure",
            "hindi_voice_message": "सिस्टम में कुछ समस्या है। कृपया दोबारा कोशिश करें, धन्यवाद।"  # Hindi for voice
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 🔥 ENHANCED USER MANAGEMENT FUNCTIONS WITH SECURITY AND HINDI VOICE

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
        
        # Check if already active
        if person.is_active:
            logger.info(f"ℹ️ {person.name} is already active")
            return Response({
                "success": False,
                "error": f"{person.name} is already active.",
                "current_status": "already_active",
                "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आपका खाता पहले से ही सक्रिय है, धन्यवाद।"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Activate the person
        person.is_active = True
        
        # Clear deactivation fields if they exist
        if hasattr(person, 'deactivated_reason'):
            person.deactivated_reason = ""
        if hasattr(person, 'deactivated_date'):
            person.deactivated_date = None
            
        person.save()
        
        logger.info(f"✅ SUCCESS: Person {person.name} activated by admin")
        
        # 🎵 Trigger Hindi voice announcement
        hindi_message = f"हैप्पी थॉट्स {person.name}, आपका खाता सफलतापूर्वक सक्रिय हो गया है, धन्यवाद।"
        try:
            speak(hindi_message)
        except Exception as voice_error:
            logger.warning(f"⚠️ Voice announcement failed: {voice_error}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been activated.",  # English for website
            "person_name": person.name,
            "person_email": person.email,
            "activated_date": timezone.now().isoformat(),
            "admin_reason": admin_reason,
            "security_status": "account_activated",
            "hindi_voice_message": hindi_message  # Hindi for voice
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
        
        # Check if already blacklisted
        if person.is_blacklisted:
            logger.info(f"ℹ️ {person.name} is already blacklisted")
            return Response({
                "success": False,
                "error": f"{person.name} is already blacklisted.",
                "current_status": "already_blacklisted",
                "existing_reason": getattr(person, 'blacklisted_reason', 'Unknown'),
                "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आप पहले से ही प्रतिबंधित सूची में हैं, धन्यवाद।"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Blacklist the person
        person.is_blacklisted = True
        
        # Set blacklist fields if they exist
        if hasattr(person, 'blacklisted_reason'):
            person.blacklisted_reason = reason
        if hasattr(person, 'blacklisted_date'):
            person.blacklisted_date = timezone.now()
            
        person.save()
        
        logger.info(f"🚫 SECURITY: Person {person.name} blacklisted by {admin_user} - Reason: {reason}")
        
        # 🎵 Trigger Hindi voice warning
        hindi_message = f"हैप्पी थॉट्स {person.name}, आपको प्रतिबंधित सूची में डाल दिया गया है। कारण: {reason}। कृपया एडमिन से संपर्क करें, धन्यवाद।"
        try:
            speak(hindi_message)
        except Exception as voice_error:
            logger.warning(f"⚠️ Voice announcement failed: {voice_error}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been blacklisted.",  # English for website
            "person_name": person.name,
            "person_email": person.email,
            "reason": reason,
            "blacklisted_date": timezone.now().isoformat(),
            "admin_user": admin_user,
            "security_status": "account_blacklisted",
            "hindi_voice_message": hindi_message  # Hindi for voice
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
        
        # Check if not blacklisted
        if not person.is_blacklisted:
            logger.info(f"ℹ️ {person.name} is not blacklisted")
            return Response({
                "success": False,
                "error": f"{person.name} is not blacklisted.",
                "current_status": "not_blacklisted",
                "hindi_voice_message": f"हैप्पी थॉट्स {person.name}, आप प्रतिबंधित सूची में नहीं हैं, धन्यवाद।"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Remove from blacklist
        person.is_blacklisted = False
        
        # Clear blacklist fields if they exist
        if hasattr(person, 'blacklisted_reason'):
            person.blacklisted_reason = ""
        if hasattr(person, 'blacklisted_date'):
            person.blacklisted_date = None
            
        person.save()
        
        logger.info(f"✅ SUCCESS: Person {person.name} removed from blacklist by {admin_user}")
        
        # 🎵 Trigger Hindi voice confirmation
        hindi_message = f"हैप्पी थॉट्स {person.name}, आपको प्रतिबंधित सूची से हटा दिया गया है। अब आप उपस्थिति दर्ज करा सकते हैं, धन्यवाद।"
        try:
            speak(hindi_message)
        except Exception as voice_error:
            logger.warning(f"⚠️ Voice announcement failed: {voice_error}")
        
        return Response({
            "success": True,
            "message": f"{person.name} has been removed from blacklist.",  # English for website
            "person_name": person.name,
            "person_email": person.email,
            "unblacklisted_date": timezone.now().isoformat(),
            "admin_reason": admin_reason,
            "admin_user": admin_user,
            "security_status": "blacklist_removed",
            "hindi_voice_message": hindi_message  # Hindi for voice
        }, status=status.HTTP_200_OK)
        
    except KnownPerson.DoesNotExist:
        logger.error(f"❌ SECURITY: Person not found for unblacklisting - {email}")
        return Response({
            "success": False,
            "error": "Person not found.",
            "security_status": "person_not_found",
            "hindi_voice_message": get_person_not_found_message()
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ CRITICAL: Error unblacklisting person - {e}")
        return Response({
            "success": False,
            "error": "System error during unblacklisting.",
            "technical_error": str(e),
            "security_status": "unblacklisting_failed",
            "hindi_voice_message": "प्रतिबंधित सूची से हटाने में समस्या है। कृपया एडमिन से संपर्क करें, धन्यवाद।"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 🔒 ADMIN FUNCTIONS WITH ENHANCED SECURITY (English responses for admin use)

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
        
        # Check if already inactive
        if not person.is_active:
            logger.info(f"ℹ️ {person.name} is already inactive")
            return Response({
                "success": False,
                "error": f"{person.name} is already inactive.",
                "current_status": "already_inactive",
                "existing_reason": getattr(person, 'deactivated_reason', 'Unknown')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Deactivate the person
        person.is_active = False
        
        # Set deactivation fields if they exist
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

# 🔒 NEW: Security audit endpoints for monitoring

@api_view(['GET'])
def attendance_audit(request):
    """🔒 NEW: Get attendance audit information for security monitoring"""
    try:
        today = timezone.now().date()
        
        # Get today's attendance statistics
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
