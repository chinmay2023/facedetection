# faceapp/admin.py
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import KnownPerson, Attendance, TejgyanSession
from .utils import encode_face_image
import pytz

class KnownPersonAdmin(admin.ModelAdmin):
    # ✅ Enhanced list display with activation status and face encoding status
    list_display = ['name', 'email', 'gender', 'city', 'shivir', 'activation_status', 'blacklist_status', 'has_face_encoding']
    list_filter = ['is_active', 'is_blacklisted', 'gender', 'city', 'shivir']
    search_fields = ['name', 'email']
    
    # ✅ Organized fieldsets with activation management
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'city', 'shivir', 'gender', 'image')
        }),
        ('Activation Management', {
            'fields': ('is_active', 'deactivated_reason', 'deactivated_date'),
            'classes': ('collapse',),
            'description': 'Manage user activation status'
        }),
        ('Blacklist Management', {
            'fields': ('is_blacklisted', 'blacklisted_reason', 'blacklisted_date'),
            'classes': ('collapse',),
            'description': 'Manage blacklist status for this person'
        }),
        ('Face Recognition Data', {
            'fields': ('encoding',),
            'classes': ('collapse',),
            'description': 'Auto-generated face encoding data'
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
        
        # ✅ FIXED: Always regenerate face encoding when image exists
        if obj.image:
            try:
                import os
                from django.conf import settings
                
                # Construct proper image path
                image_path = obj.image.path if hasattr(obj.image, 'path') else os.path.join(settings.MEDIA_ROOT, str(obj.image))
                
                # Validate image file exists
                if os.path.isfile(image_path):
                    # Always regenerate encoding (removed the 'not obj.encoding' condition)
                    encoding = encode_face_image(image_path)
                    
                    if encoding is not None:
                        obj.encoding = encoding.tobytes()
                        obj.save(update_fields=['encoding'])  # Save only encoding field
                        
                        # Success message with encoding size
                        self.message_user(
                            request, 
                            f"✅ Face encoding successfully generated for {obj.name} ({len(obj.encoding)} bytes)",
                            level='SUCCESS'
                        )
                    else:
                        # Clear any existing encoding if face detection failed
                        obj.encoding = None
                        obj.save(update_fields=['encoding'])
                        
                        self.message_user(
                            request, 
                            f"⚠️ No face detected in image for {obj.name}. Please upload a clear face photo with visible face.",
                            level='WARNING'
                        )
                else:
                    # Image file doesn't exist
                    self.message_user(
                        request, 
                        f"❌ Image file not found for {obj.name}. Please re-upload the image.",
                        level='ERROR'
                    )
                    
            except Exception as e:
                # Handle any encoding errors
                self.message_user(
                    request, 
                    f"❌ Error processing face image for {obj.name}: {str(e)}",
                    level='ERROR'
                )
        else:
            # No image provided - clear encoding
            if obj.encoding:
                obj.encoding = None
                obj.save(update_fields=['encoding'])
                self.message_user(
                    request, 
                    f"ℹ️ Face encoding cleared for {obj.name} (no image provided)",
                    level='INFO'
                )

    # ✅ Enhanced admin actions
    actions = [
        'activate_selected', 'deactivate_selected', 
        'blacklist_selected', 'unblacklist_selected',
        'regenerate_encodings_selected'
    ]
    
    # ✅ NEW: Bulk regenerate encodings action
    def regenerate_encodings_selected(self, request, queryset):
        """Regenerate face encodings for selected users"""
        success_count = 0
        error_count = 0
        
        for person in queryset:
            if person.image:
                try:
                    import os
                    from django.conf import settings
                    
                    image_path = person.image.path if hasattr(person.image, 'path') else os.path.join(settings.MEDIA_ROOT, str(person.image))
                    
                    if os.path.isfile(image_path):
                        encoding = encode_face_image(image_path)
                        if encoding is not None:
                            person.encoding = encoding.tobytes()
                            person.save(update_fields=['encoding'])
                            success_count += 1
                        else:
                            person.encoding = None
                            person.save(update_fields=['encoding'])
                            error_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
            else:
                error_count += 1
        
        if success_count > 0:
            self.message_user(request, f"✅ Successfully regenerated face encodings for {success_count} person(s).")
        if error_count > 0:
            self.message_user(request, f"⚠️ Failed to generate encodings for {error_count} person(s).")
    
    regenerate_encodings_selected.short_description = "🔄 Regenerate face encodings"
    
    # ✅ Activation actions
    def activate_selected(self, request, queryset):
        count = queryset.filter(is_active=False).update(
            is_active=True,
            deactivated_date=None,
            deactivated_reason=""
        )
        self.message_user(request, f"{count} person(s) have been activated.")
    activate_selected.short_description = "✅ Activate selected persons"
    
    def deactivate_selected(self, request, queryset):
        count = 0
        for person in queryset:
            if person.is_active:
                person.is_active = False
                person.deactivated_date = timezone.now()
                person.deactivated_reason = "Bulk deactivated by admin"
                person.save()
                count += 1
        self.message_user(request, f"{count} person(s) have been deactivated.")
    deactivate_selected.short_description = "❌ Deactivate selected persons"
    
    # Existing blacklist actions
    def blacklist_selected(self, request, queryset):
        count = 0
        for person in queryset:
            if not person.is_blacklisted:
                person.is_blacklisted = True
                person.blacklisted_date = timezone.now()
                person.blacklisted_reason = "Bulk blacklisted by admin"
                person.save()
                count += 1
        self.message_user(request, f"{count} person(s) have been blacklisted.")
    blacklist_selected.short_description = "🚫 Blacklist selected persons"
    
    def unblacklist_selected(self, request, queryset):
        count = queryset.filter(is_blacklisted=True).update(
            is_blacklisted=False,
            blacklisted_date=None,
            blacklisted_reason=""
        )
        self.message_user(request, f"{count} person(s) have been removed from blacklist.")
    unblacklist_selected.short_description = "✅ Remove from blacklist"
    
    # ✅ Custom display methods for better admin visualization
    def activation_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✅ Active</span>')
        else:
            return format_html('<span style="color: red;">❌ Inactive</span>')
    activation_status.short_description = 'Status'
    
    def blacklist_status(self, obj):
        if obj.is_blacklisted:
            return format_html('<span style="color: red;">🚫 Blacklisted</span>')
        else:
            return format_html('<span style="color: green;">✅ Clear</span>')
    blacklist_status.short_description = 'Blacklist'
    
    # ✅ NEW: Show face encoding status
    def has_face_encoding(self, obj):
        """Show if user has face encoding"""
        if obj.encoding:
            return format_html('<span style="color: green;">✅ Yes ({} bytes)</span>', len(obj.encoding))
        else:
            return format_html('<span style="color: red;">❌ No</span>')
    has_face_encoding.short_description = 'Face Encoding'

# ✅ NEW: TejgyanSession Admin for Sirshree's session management
@admin.register(TejgyanSession)
class TejgyanSessionAdmin(admin.ModelAdmin):
    list_display = ['session_name', 'session_type_display', 'session_date', 'conducted_by', 'active_status', 'created_at']
    list_filter = ['session_type', 'session_date', 'is_active', 'conducted_by']
    search_fields = ['session_name', 'conducted_by']
    date_hierarchy = 'session_date'
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_name', 'session_type', 'session_date', 'conducted_by'),
            'description': 'Basic information about the Tejgyan Foundation session'
        }),
        ('📅 Session Activation', {
            'fields': ('is_active',),
            'description': '<strong>⚠️ Important:</strong> Check this box to make this session ACTIVE for today\'s face recognition attendance marking. Only ONE session can be active at a time.',
            'classes': ('wide',)
        }),
    )
    
    def session_type_display(self, obj):
        """Enhanced session type display with spiritual context"""
        type_colors = {
            'MA': '#FF6B6B',      # Red for entry level
            'SSP1': '#4ECDC4',    # Teal for SSP1
            'SSP2': '#45B7D1',    # Blue for SSP2
            'HS1': '#96CEB4',     # Green for Higher Shivir 1
            'HS2': '#FFEAA7',     # Yellow for Higher Shivir 2
            'FESTIVAL': '#DDA0DD', # Purple for festivals
        }
        color = type_colors.get(obj.session_type, '#6C5CE7')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_session_type_display()
        )
    session_type_display.short_description = 'Session Type'
    
    def active_status(self, obj):
        """Show active session status with prominent display"""
        if obj.is_active:
            return format_html(
                '<span style="color: #27AE60; font-weight: bold; font-size: 14px;"> ACTIVE NOW</span>'
            )
        else:
            return format_html(
                '<span style="color: #7F8C8D; font-size: 12px;"> Inactive</span>'
            )
    active_status.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Enhanced save logic with active session management"""
        if obj.is_active:
            # Deactivate all other sessions before activating this one
            previously_active = TejgyanSession.objects.filter(is_active=True).exclude(pk=obj.pk)
            deactivated_count = previously_active.count()
            previously_active.update(is_active=False)
            
            # Save the current session as active
            super().save_model(request, obj, form, change)
            
            # Success message with spiritual context
            if deactivated_count > 0:
                self.message_user(
                    request, 
                    f"'{obj.session_name}' is now the ACTIVE session for Sirshree's teachings! ({deactivated_count} other session(s) automatically deactivated)",
                    level='SUCCESS'
                )
            else:
                self.message_user(
                    request, 
                    f"'{obj.session_name}' is now ACTIVE for face recognition attendance marking!",
                    level='SUCCESS'
                )
        else:
            super().save_model(request, obj, form, change)
            self.message_user(
                request, 
                f"📝 Session '{obj.session_name}' has been saved (inactive)",
                level='INFO'
            )
    
    # ✅ Enhanced admin actions for session management
    actions = ['activate_selected_session', 'deactivate_all_sessions']
    
    def activate_selected_session(self, request, queryset):
        """Activate selected session (only allows one at a time)"""
        if queryset.count() > 1:
            self.message_user(
                request, 
                "❌ You can only activate ONE session at a time. Please select only one session.",
                level='ERROR'
            )
            return
        
        session = queryset.first()
        if session:
            # Deactivate all other sessions
            TejgyanSession.objects.filter(is_active=True).update(is_active=False)
            
            # Activate selected session
            session.is_active = True
            session.save()
            
            self.message_user(
                request, 
                f"'{session.session_name}' is now the ACTIVE session for Sirshree's teachings!",
                level='SUCCESS'
            )
    activate_selected_session.short_description = " Activate selected session"
    
    def deactivate_all_sessions(self, request, queryset):
        """Deactivate all sessions"""
        count = TejgyanSession.objects.filter(is_active=True).update(is_active=False)
        self.message_user(
            request, 
            f"⚪ All sessions deactivated ({count} session(s)). Face recognition will not work until a session is activated.",
            level='WARNING'
        )
    deactivate_all_sessions.short_description = " Deactivate all sessions"

# ✅ ENHANCED: Attendance Admin with Complete User Details
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    # ✅ Show comprehensive user details in attendance list
    list_display = [
        'person_name_with_status',
        'person_email', 
        'person_city',
        'person_gender',
        'person_shivir',
        'session_info',
        'timestamp_ist',
        'session_type_badge'
    ]
    
    list_filter = [
        'session__session_type', 
        'timestamp', 
        'session__conducted_by',
        'person__is_active',           # ✅ Filter by user status
        'person__is_blacklisted',      # ✅ Filter by blacklist status
        'person__gender',              # ✅ Filter by gender
        'person__city'                 # ✅ Filter by city
    ]
    
    search_fields = [
        'person__name', 
        'person__email', 
        'session__session_name',
        'person__city',
        'person__shivir'
    ]
    
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    # ✅ Optimize database queries for related fields
    list_select_related = ['person', 'session']
    
    # ✅ Display person's name with status indicators
    def person_name_with_status(self, obj):
        person = obj.person
        status_icons = []
        
        if not person.is_active:
            status_icons.append('<span style="color: red; font-weight: bold;">❌ INACTIVE</span>')
        if person.is_blacklisted:
            status_icons.append('<span style="color: red; font-weight: bold;">🚫 BLACKLISTED</span>')
        
        status_html = ' '.join(status_icons)
        
        if status_html:
            return format_html(
                '<strong>{}</strong><br/><small>{}</small>',
                person.name,
                status_html
            )
        else:
            return format_html('<strong>{}</strong>', person.name)  # ✅ Default Django color

    
    person_name_with_status.short_description = 'Person Name & Status'
    person_name_with_status.admin_order_field = 'person__name'
    
    # ✅ Display person's email
    def person_email(self, obj):
        return obj.person.email
    person_email.short_description = 'Email'
    person_email.admin_order_field = 'person__email'
    
    # ✅ Display person's city
    def person_city(self, obj):
        return obj.person.city
    person_city.short_description = 'City'
    person_city.admin_order_field = 'person__city'
    
    # ✅ Display person's gender with icon
    def person_gender(self, obj):
        gender = obj.person.gender
        if gender == 'M':
            return ' Male'
        elif gender == 'F':
            return ' Female'
        else:
            return '-'

    person_gender.short_description = 'Gender'
    person_gender.admin_order_field = 'person__gender'
    
    # ✅ Display person's shivir background
    def person_shivir(self, obj):
        return obj.person.shivir or '-'
    person_shivir.short_description = 'Shivir Background'
    person_shivir.admin_order_field = 'person__shivir'
    
    # ✅ Enhanced session_info method
    def session_info(self, obj):
        if obj.session:
            return format_html(
                '<strong>{}</strong><br/><small style="color: #666;">Conducted by: {}</small>',
                obj.session.session_name,
                obj.session.conducted_by
            )
        return format_html('<em style="color: #999;">General attendance</em>')
    session_info.short_description = 'Session Details'
    
    # ✅ Enhanced session_type_badge method
    def session_type_badge(self, obj):
        if obj.session:
            type_colors = {
                'MA': '#FF6B6B',      # Red for MA
                'SSP1': '#4ECDC4',    # Teal for SSP1
                'SSP2': '#45B7D1',    # Blue for SSP2
                'HS1': '#96CEB4',     # Green for Higher Shivir 1
                'HS2': '#FFEAA7',     # Yellow for Higher Shivir 2
                'FESTIVAL': '#DDA0DD', # Purple for festivals
            }
            color = type_colors.get(obj.session.session_type, '#6C5CE7')
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px; font-weight: bold;">{}</span>',
                color,
                obj.session.session_type
            )
        return format_html('<span style="color: #999;">-</span>')
    session_type_badge.short_description = 'Type'
    
    # ✅ Enhanced timestamp_ist method
    def timestamp_ist(self, obj):
        ist = pytz.timezone('Asia/Kolkata')
        local_time = obj.timestamp.astimezone(ist)
        return format_html(
            '<span title="{}">{}</span>',
            local_time.strftime('%A, %B %d, %Y at %I:%M:%S %p'),
            local_time.strftime('%Y-%m-%d %H:%M:%S')
        )
    timestamp_ist.short_description = 'Time (IST)'
    
    # ✅ Optimize database queries
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('person', 'session')

# ✅ Register models with enhanced admin interfaces
admin.site.register(KnownPerson, KnownPersonAdmin)

# ✅ Enhanced admin site branding for Tejgyan Foundation
admin.site.site_header = "Tejgyan Foundation - Face Recognition Attendance"
admin.site.site_title = "Tejgyan Foundation Admin"
admin.site.index_title = "Face Recognition Attendance System by Sirshree"

# ✅ Add custom CSS for better visual experience
admin.site.extra_head = '''
<style>
.module h2 {
    background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
    background-size: 400% 400%;
    animation: gradient 15s ease infinite;
}

@keyframes gradient {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.form-row .form-label {
    font-weight: 600;
}
</style>
'''
