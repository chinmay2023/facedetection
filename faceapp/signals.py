# faceapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import (
    Attendance, 
    MA_Attendance, SSP1_Attendance, SSP2_Attendance, 
    HS1_Attendance, HS2_Attendance
)

# Session model mapping
SESSION_MODEL_MAP = {
    'MA': MA_Attendance,
    'SSP1': SSP1_Attendance, 
    'SSP2': SSP2_Attendance,
    'HS1': HS1_Attendance,
    'HS2': HS2_Attendance,
}

def get_session_duration(session_type):
    """Get duration for each session type"""
    durations = {
        'MA': 5,    # 5 days
        'SSP1': 2,  # 2 days  
        'SSP2': 2,  # 2 days
        'HS1': 2,   # 2 days
        'HS2': 2,   # 2 days
    }
    return durations.get(session_type, 1)

@receiver(post_save, sender=Attendance)
def mirror_attendance_to_session_table(sender, instance, created, **kwargs):
    """
    🚀 AUTOMATIC MIRRORING: When attendance is marked in Attendance table,
    automatically create/update corresponding entry in session-specific table
    """
    # Only process newly created attendance records
    if not created:
        return
    
    # Skip if no session is associated
    if not instance.session:
        print(f"⚠️ No session associated with attendance for {instance.person.name}")
        return
    
    session_type = instance.session.session_type
    
    # Skip FESTIVAL sessions (they don't have specific tables)
    if session_type == 'FESTIVAL':
        print(f"ℹ️ Festival attendance for {instance.person.name} - no specific table needed")
        return
    
    # Get the appropriate session model
    SessionModel = SESSION_MODEL_MAP.get(session_type)
    if not SessionModel:
        print(f"⚠️ No model found for session type: {session_type}")
        return
    
    # Get attendance date in local timezone
    attendance_date = instance.timestamp.astimezone(timezone.get_current_timezone()).date()
    person = instance.person
    session_reference = instance.session
    
    print(f"🔄 Mirroring attendance: {person.name} -> {session_type} on {attendance_date}")
    
    try:
        # Check if session attendance already exists for this person and session
        existing_attendance = SessionModel.objects.filter(
            person=person,
            session_reference=session_reference
        ).first()
        
        session_duration = get_session_duration(session_type)
        
        if existing_attendance:
            # User is continuing an existing session
            if existing_attendance.is_completed:
                print(f"ℹ️ {person.name} already completed {session_type} - no update needed")
                return
            
            # Increment day number for continuing session
            if existing_attendance.day_number < session_duration:
                existing_attendance.day_number += 1
                existing_attendance.attendance_date = attendance_date
                
                # Mark as completed if final day reached
                if existing_attendance.day_number >= session_duration:
                    existing_attendance.is_completed = True
                    print(f"🎉 {person.name} completed {session_type}! ({existing_attendance.day_number}/{session_duration})")
                    
                    # Trigger automatic shivir field update
                    try:
                        success = person.update_shivir_field_on_completion(session_type)
                        if success:
                            print(f"✅ Shivir field auto-updated for {person.name}")
                    except Exception as e:
                        print(f"⚠️ Shivir field update error for {person.name}: {e}")
                else:
                    print(f"📅 {person.name} - {session_type} Day {existing_attendance.day_number}/{session_duration}")
                
                existing_attendance.save()
            
        else:
            # Create new session attendance record (Day 1)
            new_attendance = SessionModel.objects.create(
                person=person,
                attendance_date=attendance_date,
                day_number=1,
                session_reference=session_reference,
                is_completed=(session_duration == 1)  # Single day sessions complete immediately
            )
            
            print(f"✅ Created new {session_type} attendance: {person.name} - Day 1/{session_duration}")
            
            # Handle single-day session completion
            if session_duration == 1:
                print(f"🎉 {person.name} completed single-day {session_type}!")
                try:
                    success = person.update_shivir_field_on_completion(session_type)
                    if success:
                        print(f"✅ Shivir field auto-updated for {person.name}")
                except Exception as e:
                    print(f"⚠️ Shivir field update error for {person.name}: {e}")
    
    except Exception as e:
        print(f"❌ Error mirroring attendance for {person.name}: {e}")

print(" Face Recognition Attendance Signals Loaded Successfully!")
