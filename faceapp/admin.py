# faceapp/admin.py - ENHANCED VERSION WITH DYNAMIC COMPLETED FIELD
from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from datetime import date, timedelta
from .models import (
    KnownPerson, Attendance, TejgyanSession,
    MA_Attendance, SSP1_Attendance, SSP2_Attendance, HS1_Attendance, HS2_Attendance,
    MA_Repeaters, SSP1_Repeaters, SSP2_Repeaters, HS1_Repeaters, HS2_Repeaters
)
from .utils import encode_face_image
import pytz


# ================================
# KNOWN PERSON ADMIN - FIXED DYNAMIC COMPLETED FIELD + CLEAN SHIVIR DISPLAY
# ================================


@admin.register(KnownPerson)
class KnownPersonAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'email', 
        'city',
        'gender',
        'shivir_clean_display',  # 🔧 FIXED: Shows clean shivir without "_COMPLETED"
        'get_spiritual_level',
        'next_eligible_session',        
        'get_dynamic_completion_status',   # 🔥 FIXED: Now fully dynamic
        'get_total_attendance',
        'activation_status',
        'blacklist_status',
        'has_face_encoding'
    ]
    list_filter = [
        'is_active', 'is_blacklisted', 'gender', 'city', 'shivir',
    ]
    search_fields = ['name', 'email', 'city', 'shivir']
    ordering = ['name']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'city', 'shivir', 'gender', 'image'),
        }),
        ('Activation Management', {
            'fields': ('is_active', 'deactivated_reason', 'deactivated_date'),
        }),
        ('Blacklist Management', {
            'fields': ('is_blacklisted', 'blacklisted_reason', 'blacklisted_date'),
        }),
        ('Face Recognition Data', {
            'fields': ('encoding',),
        }),
    )
    
    readonly_fields = ['encoding', 'blacklisted_date', 'deactivated_date']
    
    def save_model(self, request, obj, form, change):
        # Handle blacklist date automatically
        if obj.is_blacklisted and not obj.blacklisted_date:
            obj.blacklisted_date = timezone.now()
        elif not obj.is_blacklisted:
            obj.blacklisted_date = None
            obj.blacklisted_reason = ""
        
        # Handle deactivation date automatically
        if not obj.is_active and not obj.deactivated_date:
            obj.deactivated_date = timezone.now()
        elif obj.is_active:
            obj.deactivated_date = None
            obj.deactivated_reason = ""
        
        # Save the object first
        super().save_model(request, obj, form, change)
        
        # Generate face encoding when image exists
        if obj.image:
            try:
                import os
                from django.conf import settings
                
                image_path = obj.image.path if hasattr(obj.image, 'path') else os.path.join(settings.MEDIA_ROOT, str(obj.image))
                
                if os.path.isfile(image_path):
                    encoding = encode_face_image(image_path)
                    
                    if encoding is not None:
                        obj.encoding = encoding.tobytes()
                        obj.save(update_fields=['encoding'])
                        self.message_user(request, f"Face encoding generated for {obj.name}", messages.SUCCESS)
                    else:
                        obj.encoding = None
                        obj.save(update_fields=['encoding'])
                        self.message_user(request, f"No face detected for {obj.name}", messages.WARNING)
                else:
                    self.message_user(request, f"Image file not found for {obj.name}", messages.ERROR)
                    
            except Exception as e:
                self.message_user(request, f"Error processing image for {obj.name}: {str(e)}", messages.ERROR)
        else:
            if obj.encoding:
                obj.encoding = None
                obj.save(update_fields=['encoding'])
    
    def get_spiritual_level(self, obj):
        """Display spiritual level"""
        level = obj.get_shivir_background_level()
        return level if level else "New User"
    get_spiritual_level.short_description = 'Spiritual Level'
    
    # 🔧 NEW: Clean Shivir Display Method for Admin
    def shivir_clean_display(self, obj):
        """Display clean shivir without '_COMPLETED' suffixes"""
        return obj.get_clean_shivir_display()
    shivir_clean_display.short_description = 'Shivir Background'
    shivir_clean_display.admin_order_field = 'shivir'  # Allow sorting by original field
    
    @admin.display(description='Next Eligible')
    def next_eligible_session(self, obj):
        """Show the next session this user is eligible to attend"""
        progression_order = ['MA', 'SSP1', 'SSP2', 'HS1', 'HS2']
        current_level = obj.get_shivir_background_level()
        
        if not current_level:
            return "MA"
        
        try:
            current_index = progression_order.index(current_level)
            if current_index + 1 < len(progression_order):
                return progression_order[current_index + 1]
            else:
                return "All Sessions Complete"
        except ValueError:
            return "MA"
    
    # 🔥 FIXED: Completely Dynamic Completion Status Based on Current Active Session
    @admin.display(description='Completed')
    def get_dynamic_completion_status(self, obj):
        """
        🚀 DYNAMIC: Show completion status for CURRENT ACTIVE SESSION ONLY
        Updates immediately when shivir field changes
        """
        try:
            # Get current active session
            active_session = TejgyanSession.objects.filter(is_active=True).first()
            
            if not active_session:
                return "No Active Session"
            
            session_type = active_session.session_type
            user_shivir = obj.shivir or ""
            
            # Session duration mapping
            session_durations = {
                'MA': 5, 'SSP1': 2, 'SSP2': 2, 'HS1': 2, 'HS2': 2, 'FESTIVAL': 1
            }
            max_days = session_durations.get(session_type, 1)
            
            # Get appropriate attendance model
            attendance_models = {
                'MA': MA_Attendance,
                'SSP1': SSP1_Attendance, 
                'SSP2': SSP2_Attendance,
                'HS1': HS1_Attendance,
                'HS2': HS2_Attendance
            }
            
            AttendanceModel = attendance_models.get(session_type)
            
            if not AttendanceModel:
                return "Invalid Session Type"
            
            # Check current session progress for this specific active session
            attendance = AttendanceModel.objects.filter(
                person=obj,
                session_reference=active_session
            ).first()
            
            if attendance:
                # User has attendance record for current active session
                if attendance.is_completed:
                    return f"✅ {session_type} Completed"
                else:
                    return f"{session_type} ({attendance.day_number}/{max_days})"
            else:
                # No attendance record for current active session
                # Check if user is eligible based on their shivir background
                user_level = obj.get_shivir_background_level()
                eligible_sessions = self.get_user_eligible_sessions(obj, user_level)
                
                if session_type in eligible_sessions:
                    return "Not Started"
                else:
                    return "None"
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_user_eligible_sessions(self, person, user_shivir_level):
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
    
    # Make it sortable
    get_dynamic_completion_status.admin_order_field = 'shivir'
    
    def get_total_attendance(self, obj):
        """Display total attendance count"""
        total = Attendance.objects.filter(person=obj).count()
        return str(total)
    get_total_attendance.short_description = 'Total Attendance'
    
    def activation_status(self, obj):
        return "Active" if obj.is_active else "Inactive"
    activation_status.short_description = 'Status'
    
    def blacklist_status(self, obj):
        return "Blacklisted" if obj.is_blacklisted else "Clear"
    blacklist_status.short_description = 'Blacklist'
    
    def has_face_encoding(self, obj):
        if obj.encoding:
            return f"Yes ({len(obj.encoding)} bytes)"
        else:
            return "No"
    has_face_encoding.short_description = 'Face Encoding'
    
    # Admin actions
    actions = ['activate_selected', 'deactivate_selected', 'blacklist_selected', 'unblacklist_selected']
    
    def activate_selected(self, request, queryset):
        count = queryset.filter(is_active=False).update(
            is_active=True,
            deactivated_date=None,
            deactivated_reason=""
        )
        self.message_user(request, f"{count} person(s) activated.", messages.SUCCESS)
    activate_selected.short_description = "Activate selected persons"
    
    def deactivate_selected(self, request, queryset):
        count = 0
        for person in queryset:
            if person.is_active:
                person.is_active = False
                person.deactivated_date = timezone.now()
                person.deactivated_reason = "Bulk deactivated by admin"
                person.save()
                count += 1
        self.message_user(request, f"{count} person(s) deactivated.", messages.WARNING)
    deactivate_selected.short_description = "Deactivate selected persons"
    
    def blacklist_selected(self, request, queryset):
        count = 0
        for person in queryset:
            if not person.is_blacklisted:
                person.is_blacklisted = True
                person.blacklisted_date = timezone.now()
                person.blacklisted_reason = "Bulk blacklisted by admin"
                person.save()
                count += 1
        self.message_user(request, f"{count} person(s) blacklisted.", messages.ERROR)
    blacklist_selected.short_description = "Blacklist selected persons"
    
    def unblacklist_selected(self, request, queryset):
        count = queryset.filter(is_blacklisted=True).update(
            is_blacklisted=False,
            blacklisted_date=None,
            blacklisted_reason=""
        )
        self.message_user(request, f"{count} person(s) removed from blacklist.", messages.SUCCESS)
    unblacklist_selected.short_description = "Remove from blacklist"


# ================================
# ATTENDANCE ADMIN CLASSES
# ================================


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'person_name',
        'person_email',
        'session_name',
        'session_type',
        'timestamp_ist',
        'person_status'
    ]
    list_filter = [
        'session__session_type',
        'session__session_date',
        'timestamp',
        'person__is_active',
        'person__is_blacklisted',
        'person__gender',
        'person__city'
    ]
    search_fields = [
        'person__name', 
        'person__email', 
        'session__session_name',
        'person__city'
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    list_select_related = ['person', 'session']
    list_per_page = 50
    
    def person_name(self, obj):
        return obj.person.name if obj.person else "Unknown"
    person_name.short_description = 'Name'
    person_name.admin_order_field = 'person__name'
    
    def person_email(self, obj):
        return obj.person.email if obj.person else "Unknown"
    person_email.short_description = 'Email'
    person_email.admin_order_field = 'person__email'
    
    def session_name(self, obj):
        return obj.session.session_name if obj.session else "General Attendance"
    session_name.short_description = 'Session Name'
    
    def session_type(self, obj):
        return obj.session.session_type if obj.session else ""
    session_type.short_description = 'Session Type'
    
    def timestamp_ist(self, obj):
        ist = pytz.timezone('Asia/Kolkata')
        local_time = obj.timestamp.astimezone(ist)
        return local_time.strftime('%Y-%m-%d %H:%M:%S IST')
    timestamp_ist.short_description = 'Timestamp (IST)'
    timestamp_ist.admin_order_field = 'timestamp'
    
    def person_status(self, obj):
        person = obj.person
        if not person.is_active:
            return "Inactive User"
        elif person.is_blacklisted:
            return "Blacklisted User"
        else:
            return "Valid"
    person_status.short_description = 'Status'


class BaseSessionAttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'person_name',
        'day_number',
        'attendance_date',
        'is_completed',
        'session_reference_name'
    ]
    list_filter = [
        'is_completed',
        'attendance_date',
        'day_number',
        'person__is_active',
        'person__is_blacklisted'
    ]
    search_fields = ['person__name', 'person__email']
    ordering = ['-attendance_date', 'person__name']
    date_hierarchy = 'attendance_date'
    list_select_related = ['person', 'session_reference']
    
    def person_name(self, obj):
        return obj.person.name if obj.person else "Unknown"
    person_name.short_description = 'Person Name'
    person_name.admin_order_field = 'person__name'
    
    def session_reference_name(self, obj):
        if hasattr(obj, 'session_reference') and obj.session_reference:
            return f"{obj.session_reference.session_name} by {obj.session_reference.conducted_by}"
        return "No reference"
    session_reference_name.short_description = 'Session Reference'


@admin.register(MA_Attendance)
class MA_AttendanceAdmin(BaseSessionAttendanceAdmin):
    pass


@admin.register(SSP1_Attendance) 
class SSP1_AttendanceAdmin(BaseSessionAttendanceAdmin):
    pass


@admin.register(SSP2_Attendance)
class SSP2_AttendanceAdmin(BaseSessionAttendanceAdmin):
    pass


@admin.register(HS1_Attendance)
class HS1_AttendanceAdmin(BaseSessionAttendanceAdmin):
    pass


@admin.register(HS2_Attendance)
class HS2_AttendanceAdmin(BaseSessionAttendanceAdmin):
    pass


# ================================
# ✅ ENHANCED REPEATER ADMIN CLASSES WITH NEW COLUMNS
# ================================


class BaseRepeaterAdmin(admin.ModelAdmin):
    list_display = [
        'person_name',
        'repeat_attendance_date',
        'get_session_progress',  # ✅ NEW: Shows "Day X/Y"
        'get_completion_status',  # ✅ NEW: Shows completion status
        'session_reference_display',  # ✅ NEW: Shows linked session
        'previous_attendance_date',
        'days_gap',
        'repeat_count'
    ]
    list_filter = [
        'is_completed',  # ✅ NEW: Filter by completion status
        'day_number',    # ✅ NEW: Filter by day number
        'repeat_attendance_date',
        'days_gap',
        'repeat_count',
        'person__is_active',
        'person__is_blacklisted',
        'session_reference__session_type'  # ✅ NEW: Filter by session type
    ]
    search_fields = ['person__name', 'person__email', 'session_reference__session_name']
    ordering = ['-repeat_attendance_date', 'person__name']
    date_hierarchy = 'repeat_attendance_date'
    list_select_related = ['person', 'session_reference']  # ✅ NEW: Include session_reference
    
    def person_name(self, obj):
        return obj.person.name if obj.person else "Unknown"
    person_name.short_description = 'Person Name'
    person_name.admin_order_field = 'person__name'
    
    # ✅ NEW: Display session progress (Day X/Y)
    def get_session_progress(self, obj):
        """Show session day progression like 'Day 2/5' or 'Day 1/2'"""
        # Determine session duration based on the model type
        model_name = obj.__class__.__name__
        if 'MA' in model_name:
            total_days = 5
        else:  # SSP1, SSP2, HS1, HS2
            total_days = 2
        
        return f"Day {obj.day_number}/{total_days}"
    get_session_progress.short_description = 'Session Progress'
    get_session_progress.admin_order_field = 'day_number'
    
    # ✅ NEW: Display completion status with visual indicators
    def get_completion_status(self, obj):
        """Show completion status with checkmarks"""
        if obj.is_completed:
            return "✅ Completed"
        else:
            return "🔄 In Progress"
    get_completion_status.short_description = 'Completion Status'
    get_completion_status.admin_order_field = 'is_completed'
    
    # ✅ NEW: Display linked session information
    def session_reference_display(self, obj):
        """Show linked session information"""
        if obj.session_reference:
            return f"{obj.session_reference.session_name} ({obj.session_reference.session_type})"
        return "No Session Linked"
    session_reference_display.short_description = 'Linked Session'
    session_reference_display.admin_order_field = 'session_reference__session_name'


# ✅ ENHANCED: All Repeater Admin Classes with Session-Specific Details
@admin.register(MA_Repeaters)
class MA_RepeatersAdmin(BaseRepeaterAdmin):
    list_display = BaseRepeaterAdmin.list_display + ['get_ma_specific_info']
    
    def get_ma_specific_info(self, obj):
        """MA-specific information"""
        if obj.is_completed:
            return f"MA Repeat {obj.repeat_count} ✅"
        else:
            return f"MA Repeat {obj.repeat_count} - Day {obj.day_number}/5"
    get_ma_specific_info.short_description = 'MA Details'


@admin.register(SSP1_Repeaters)
class SSP1_RepeatersAdmin(BaseRepeaterAdmin):
    list_display = BaseRepeaterAdmin.list_display + ['get_ssp1_specific_info']
    
    def get_ssp1_specific_info(self, obj):
        """SSP1-specific information"""
        if obj.is_completed:
            return f"SSP1 Repeat {obj.repeat_count} ✅"
        else:
            return f"SSP1 Repeat {obj.repeat_count} - Day {obj.day_number}/2"
    get_ssp1_specific_info.short_description = 'SSP1 Details'


@admin.register(SSP2_Repeaters)
class SSP2_RepeatersAdmin(BaseRepeaterAdmin):
    list_display = BaseRepeaterAdmin.list_display + ['get_ssp2_specific_info']
    
    def get_ssp2_specific_info(self, obj):
        """SSP2-specific information"""
        if obj.is_completed:
            return f"SSP2 Repeat {obj.repeat_count} ✅"
        else:
            return f"SSP2 Repeat {obj.repeat_count} - Day {obj.day_number}/2"
    get_ssp2_specific_info.short_description = 'SSP2 Details'


@admin.register(HS1_Repeaters)
class HS1_RepeatersAdmin(BaseRepeaterAdmin):
    list_display = BaseRepeaterAdmin.list_display + ['get_hs1_specific_info']
    
    def get_hs1_specific_info(self, obj):
        """HS1-specific information"""
        if obj.is_completed:
            return f"HS1 Repeat {obj.repeat_count} ✅"
        else:
            return f"HS1 Repeat {obj.repeat_count} - Day {obj.day_number}/2"
    get_hs1_specific_info.short_description = 'HS1 Details'


@admin.register(HS2_Repeaters)
class HS2_RepeatersAdmin(BaseRepeaterAdmin):
    list_display = BaseRepeaterAdmin.list_display + ['get_hs2_specific_info']
    
    def get_hs2_specific_info(self, obj):
        """HS2-specific information"""
        if obj.is_completed:
            return f"HS2 Repeat {obj.repeat_count} ✅"
        else:
            return f"HS2 Repeat {obj.repeat_count} - Day {obj.day_number}/2"
    get_hs2_specific_info.short_description = 'HS2 Details'


# ================================
# TEJGYAN SESSION ADMIN
# ================================


@admin.register(TejgyanSession)
class TejgyanSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_name', 
        'session_type', 
        'session_date', 
        'conducted_by', 
        'is_active',
        'get_attendance_count'
    ]
    list_filter = ['session_type', 'session_date', 'is_active', 'conducted_by']
    search_fields = ['session_name', 'conducted_by']
    date_hierarchy = 'session_date'
    ordering = ['-session_date', '-created_at']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_name', 'session_type', 'session_date', 'conducted_by'),
        }),
        ('Session Activation', {
            'fields': ('is_active',),
            'description': 'Only ONE session can be active at a time for face recognition.'
        }),
    )
    
    def get_attendance_count(self, obj):
        """Show total attendance for this session"""
        total = Attendance.objects.filter(session=obj).count()
        return str(total)
    get_attendance_count.short_description = 'Total Attendance'
    
    def save_model(self, request, obj, form, change):
        if obj.is_active:
            previously_active = TejgyanSession.objects.filter(is_active=True).exclude(pk=obj.pk)
            deactivated_count = previously_active.count()
            previously_active.update(is_active=False)
            
            super().save_model(request, obj, form, change)
            
            if deactivated_count > 0:
                self.message_user(
                    request, 
                    f"'{obj.session_name}' is now ACTIVE! ({deactivated_count} other sessions deactivated)",
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request, 
                    f"'{obj.session_name}' is now ACTIVE for face recognition!",
                    messages.SUCCESS
                )
        else:
            super().save_model(request, obj, form, change)
    
    actions = ['activate_selected_session', 'deactivate_all_sessions']
    
    def activate_selected_session(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(
                request, 
                "You can only activate ONE session at a time.",
                messages.ERROR
            )
            return
        
        session = queryset.first()
        if session:
            TejgyanSession.objects.filter(is_active=True).update(is_active=False)
            session.is_active = True
            session.save()
            
            self.message_user(
                request, 
                f"'{session.session_name}' is now ACTIVE!",
                messages.SUCCESS
            )
    activate_selected_session.short_description = "Activate selected session"
    
    def deactivate_all_sessions(self, request, queryset):
        count = TejgyanSession.objects.filter(is_active=True).update(is_active=False)
        self.message_user(
            request, 
            f"All sessions deactivated ({count} sessions). Face recognition disabled.",
            messages.WARNING
        )
    deactivate_all_sessions.short_description = "Deactivate all sessions"


admin.site.site_header = "Tejgyan Foundation - Face Recognition Attendance System"
admin.site.site_title = "Tejgyan Foundation Admin"
admin.site.index_title = "Attendance Management System"
