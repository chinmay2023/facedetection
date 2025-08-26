# faceapp/signals.py - ENHANCED WITH KNOWNNPERSON SYNC SIGNALS
# 🔧 FIXED: Day numbering bug in mirror_attendance_to_session_table function
from django.db.models.signals import post_save, post_delete
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
    🔧 FIXED: Prevents Day 2 bug by properly handling session detection and same-day checks
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
        # 🔧 FIXED: Check for CURRENT ACTIVE SESSION attendance only (not just any old record)
        existing_attendance = SessionModel.objects.filter(
            person=person,
            session_reference=session_reference  # Only check THIS SPECIFIC session
        ).first()
        
        session_duration = get_session_duration(session_type)
        
        if existing_attendance:
            # 🔧 FIXED: Better validation for existing records
            if existing_attendance.is_completed:
                print(f"ℹ️ {person.name} already completed {session_type} - no update needed")
                return
            
            # 🔧 FIXED: Only increment if attendance is for a NEW day (prevent same-day duplicates)
            if existing_attendance.attendance_date == attendance_date:
                print(f"ℹ️ {person.name} already marked for {session_type} on {attendance_date} - no increment needed")
                return
            
            # 🔧 FIXED: Increment day number for CONTINUING session on NEW day
            if existing_attendance.day_number < session_duration:
                print(f"📅 Incrementing {person.name} from Day {existing_attendance.day_number} to Day {existing_attendance.day_number + 1}")
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
                print(f"⚠️ {person.name} has already reached max days for {session_type}")
            
        else:
            # 🔧 FIXED: Create new session attendance record (Day 1)
            print(f"🚀 Creating NEW {session_type} attendance for {person.name} - Day 1")
            new_attendance = SessionModel.objects.create(
                person=person,
                attendance_date=attendance_date,
                day_number=1,  # ✅ Always start at Day 1 for new sessions
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



# 🚀 NEW: SYNC SIGNALS FOR KNOWNNPERSON UPDATES
# These signals ensure KnownPerson data stays synchronized when session attendance records change


@receiver(post_save, sender=MA_Attendance)
def sync_known_person_on_ma_update(sender, instance, created, **kwargs):
    """🔄 Sync KnownPerson when MA_Attendance is created/updated"""
    try:
        person = instance.person
        # Refresh the completed sessions cache
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - MA Day {instance.day_number}")
        
        # Log completion status for admin visibility
        if instance.is_completed:
            print(f"🎉 MA Session completed for {person.name}!")
            
    except Exception as e:
        print(f"❌ Error syncing KnownPerson for MA_Attendance: {e}")



@receiver(post_save, sender=SSP1_Attendance)
def sync_known_person_on_ssp1_update(sender, instance, created, **kwargs):
    """🔄 Sync KnownPerson when SSP1_Attendance is created/updated"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - SSP1 Day {instance.day_number}")
        
        if instance.is_completed:
            print(f"🎉 SSP1 Session completed for {person.name}!")
            
    except Exception as e:
        print(f"❌ Error syncing KnownPerson for SSP1_Attendance: {e}")



@receiver(post_save, sender=SSP2_Attendance)
def sync_known_person_on_ssp2_update(sender, instance, created, **kwargs):
    """🔄 Sync KnownPerson when SSP2_Attendance is created/updated"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - SSP2 Day {instance.day_number}")
        
        if instance.is_completed:
            print(f"🎉 SSP2 Session completed for {person.name}!")
            
    except Exception as e:
        print(f"❌ Error syncing KnownPerson for SSP2_Attendance: {e}")



@receiver(post_save, sender=HS1_Attendance)
def sync_known_person_on_hs1_update(sender, instance, created, **kwargs):
    """🔄 Sync KnownPerson when HS1_Attendance is created/updated"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - HS1 Day {instance.day_number}")
        
        if instance.is_completed:
            print(f"🎉 HS1 Session completed for {person.name}!")
            
    except Exception as e:
        print(f"❌ Error syncing KnownPerson for HS1_Attendance: {e}")



@receiver(post_save, sender=HS2_Attendance)
def sync_known_person_on_hs2_update(sender, instance, created, **kwargs):
    """🔄 Sync KnownPerson when HS2_Attendance is created/updated"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - HS2 Day {instance.day_number}")
        
        if instance.is_completed:
            print(f"🎉 HS2 Session completed for {person.name}!")
            
    except Exception as e:
        print(f"❌ Error syncing KnownPerson for HS2_Attendance: {e}")



# 🚀 NEW: DELETE SIGNALS FOR KNOWNNPERSON SYNC
# These handle when attendance records are deleted (like in your bug scenario)


@receiver(post_delete, sender=MA_Attendance)
def sync_known_person_on_ma_delete(sender, instance, **kwargs):
    """🔄 Sync KnownPerson when MA_Attendance is deleted"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - MA attendance deleted")
        
    except Exception as e:
        print(f"❌ Error syncing KnownPerson on MA_Attendance delete: {e}")



@receiver(post_delete, sender=SSP1_Attendance)
def sync_known_person_on_ssp1_delete(sender, instance, **kwargs):
    """🔄 Sync KnownPerson when SSP1_Attendance is deleted"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - SSP1 attendance deleted")
        
    except Exception as e:
        print(f"❌ Error syncing KnownPerson on SSP1_Attendance delete: {e}")



@receiver(post_delete, sender=SSP2_Attendance)
def sync_known_person_on_ssp2_delete(sender, instance, **kwargs):
    """🔄 Sync KnownPerson when SSP2_Attendance is deleted"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - SSP2 attendance deleted")
        
    except Exception as e:
        print(f"❌ Error syncing KnownPerson on SSP2_Attendance delete: {e}")



@receiver(post_delete, sender=HS1_Attendance)
def sync_known_person_on_hs1_delete(sender, instance, **kwargs):
    """🔄 Sync KnownPerson when HS1_Attendance is deleted"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - HS1 attendance deleted")
        
    except Exception as e:
        print(f"❌ Error syncing KnownPerson on HS1_Attendance delete: {e}")



@receiver(post_delete, sender=HS2_Attendance)
def sync_known_person_on_hs2_delete(sender, instance, **kwargs):
    """🔄 Sync KnownPerson when HS2_Attendance is deleted"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - HS2 attendance deleted")
        
    except Exception as e:
        print(f"❌ Error syncing KnownPerson on HS2_Attendance delete: {e}")



# 🚀 NEW: GENERAL ATTENDANCE DELETE SIGNAL
@receiver(post_delete, sender=Attendance)
def sync_known_person_on_general_attendance_delete(sender, instance, **kwargs):
    """🔄 Sync KnownPerson when general Attendance is deleted"""
    try:
        person = instance.person
        person.refresh_completed_sessions_cache()
        print(f"✅ Synced KnownPerson for {person.name} - General attendance deleted")
        
    except Exception as e:
        print(f"❌ Error syncing KnownPerson on Attendance delete: {e}")



print("🔄 Face Recognition Attendance Signals with KnownPerson Sync Loaded Successfully!")
