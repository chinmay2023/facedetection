# faceapp/models.py - ENHANCED VERSION WITH ROBUST AUTO SHIVIR FIELD UPDATE
from django.db import models
from .storage import OverwriteStorage
import pytz  # ✅ For timezone conversion
from django.utils import timezone  # ✅ For timezone handling


class KnownPerson(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=100)
    shivir = models.CharField(max_length=100)  # User's shivir background - KEY FIELD FOR AUTO-UPDATE
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default=False)
    image = models.ImageField(upload_to='known_faces/',storage= OverwriteStorage(), null=True, blank=True) 
    encoding = models.BinaryField(blank=True, null=True)
    
    # Blacklist feature
    is_blacklisted = models.BooleanField(default=False, help_text="If checked, attendance will not be marked for this person")
    blacklisted_reason = models.CharField(max_length=200, blank=True, null=True, help_text="Reason for blacklisting")
    blacklisted_date = models.DateTimeField(blank=True, null=True, help_text="Date when person was blacklisted")
    
    # Activation/Deactivation feature
    is_active = models.BooleanField(default=True, help_text="Designates whether this user is active. Inactive users won't appear in face recognition.")
    deactivated_date = models.DateTimeField(blank=True, null=True, help_text="Date when person was deactivated")
    deactivated_reason = models.CharField(max_length=200, blank=True, null=True, help_text="Reason for deactivation")

    def __str__(self):
        status_parts = []
        if not self.is_active:
            status_parts.append("INACTIVE")
        if self.is_blacklisted:
            status_parts.append("BLACKLISTED")
        
        status = f" ({' & '.join(status_parts)})" if status_parts else ""
        return f"{self.name}{status}"
    
    # ✅ ENHANCED: Detect shivir background level from user's shivir field
    def get_shivir_background_level(self):
        """Detect user's shivir background level from their shivir field"""
        if not self.shivir:
            return None  # No shivir background
        
        # Clean the shivir field for matching
        shivir_clean = self.shivir.strip().upper()
        
        # Direct pattern matching (most specific first)
        shivir_patterns = [
            (['HS2', 'HIGHER SHIVIR 2', 'HS-2', 'HS 2'], 'HS2'),
            (['HS1', 'HIGHER SHIVIR 1', 'HS-1', 'HS 1', 'HIGHER SHIVIR'], 'HS1'),
            (['SSP2', 'SSP-2', 'SSP 2', 'MTS 2', 'MTS2'], 'SSP2'),
            (['SSP1', 'SSP-1', 'SSP 1', 'MTS 1', 'MTS1', 'MTS'], 'SSP1'),
            (['MA', 'MA SHIVIR', 'BASIC', 'FOUNDATION'], 'MA'),
        ]
        
        # Check for pattern matches
        for patterns, level in shivir_patterns:
            for pattern in patterns:
                if pattern in shivir_clean:
                    return level
        
        # Fallback: Check if it contains any session keywords
        if any(keyword in shivir_clean for keyword in ['SHIVIR', 'SESSION', 'COURSE']):
            # If it mentions shivir but no specific level detected, assume MA
            return 'MA'
        
        return None  # No recognizable shivir background
    
    def get_completed_sessions(self):
        """Get list of completed session types for this person"""
        completed = self.attendance_set.filter(
            session__isnull=False
        ).values_list('session__session_type', flat=True).distinct()
        return list(completed)
    
    def get_completed_sessions_display(self):
        """Get user-friendly display of completed sessions for admin"""
        completed = self.get_completed_sessions()
        if not completed:
            return "None"
        return ", ".join(completed)
    
    def get_highest_completed_session(self):
        """Get the highest completed session in progression order"""
        progression_order = ['MA', 'SSP1', 'SSP2', 'HS1', 'HS2']
        completed_sessions = self.get_completed_sessions()
        
        highest_index = -1
        for session in completed_sessions:
            if session in progression_order:
                index = progression_order.index(session)
                if index > highest_index:
                    highest_index = index
        
        if highest_index == -1:
            return None
        return progression_order[highest_index]
    
    # 🎯 ENHANCED: Simple shivir field based eligibility with auto-update integration
    def get_eligible_sessions_based_on_shivir(self):
        """
        ENHANCED: Simple eligibility based ONLY on user's shivir field
        - shivir = "MA" → Eligible for: MA, SSP1, FESTIVAL
        - shivir = "SSP1" → Eligible for: MA, SSP1, SSP2, FESTIVAL
        - shivir = "SSP2" → Eligible for: MA, SSP1, SSP2, HS1, FESTIVAL
        - shivir = "HS1" → Eligible for: MA, SSP1, SSP2, HS1, HS2, FESTIVAL
        - shivir = "HS2" → Eligible for: All sessions
        """
        progression_order = ['MA', 'SSP1', 'SSP2', 'HS1', 'HS2']
        shivir_background_level = self.get_shivir_background_level()
        
        # Handle new users with no shivir background
        if not shivir_background_level:
            return ['MA']
        
        # Find user's level in progression
        try:
            current_level_index = progression_order.index(shivir_background_level)
            
            # Build eligible sessions list:
            # 1. All previous levels (for revisiting)
            # 2. Current level (for revisiting)
            # 3. Next level (for progression)
            eligible_sessions = []
            
            # Add all completed levels + current level
            for i in range(current_level_index + 1):
                eligible_sessions.append(progression_order[i])
            
            # Add next level if exists
            if current_level_index + 1 < len(progression_order):
                next_level = progression_order[current_level_index + 1]
                eligible_sessions.append(next_level)
            
            return eligible_sessions
            
        except ValueError:
            # Unknown shivir level - treat as new user
            return ['MA']
    
    def get_eligible_next_sessions(self):
        """Get list of sessions this person is eligible for (includes FESTIVAL for face recognition)"""
        # Get the base eligibility without festivals
        eligible_sessions = self.get_eligible_sessions_based_on_shivir()
        
        # Add festivals for face recognition system (but not for admin display)
        eligible_sessions_with_festival = eligible_sessions.copy()
        eligible_sessions_with_festival.append('FESTIVAL')
        
        return eligible_sessions_with_festival
    
    def is_eligible_for_session(self, session_type):
        """🎯 ENHANCED: Check eligibility based ONLY on shivir field"""
        if session_type == 'FESTIVAL':
            return True  # Festivals are always available to everyone
        
        return session_type in self.get_eligible_sessions_based_on_shivir()
    
    def get_spiritual_progress_display(self):
        """Get a user-friendly display of spiritual progress based on shivir field"""
        shivir_background = self.get_shivir_background_level()
        eligible = self.get_eligible_sessions_based_on_shivir()
        completed = self.get_completed_sessions()
        
        # Build comprehensive display
        parts = []
        
        # Add shivir background info
        if shivir_background:
            parts.append(f"Shivir Level: {shivir_background}")
        else:
            return "New User - Ready for MA Shivir"
        
        # Add eligible sessions based on shivir field
        parts.append(f"Eligible for: {', '.join(eligible)}")
        
        # Add completed sessions info (for reference)
        if completed:
            parts.append(f"Attendance Records: {', '.join(completed)}")
        
        return " | ".join(parts)
    
    # ✅ ENHANCED: Helper method to show shivir background for admin
    def get_shivir_background_display(self):
        """Get shivir background for admin display"""
        background = self.get_shivir_background_level()
        if background:
            return f"{background} Level"
        else:
            return "New User"
    
    # 🚀 ENHANCED AUTOMATIC SHIVIR FIELD UPDATE FEATURE
    def update_shivir_field_on_completion(self, completed_session_type):
        """
        🚀 ENHANCED AUTOMATIC SHIVIR FIELD UPDATE FEATURE
        
        This method automatically updates the user's shivir field when they complete a session.
        
        INTEGRATION USAGE:
        - Call this method when user completes final day of any session
        - In face_recognize_live.py: matched_person.update_shivir_field_on_completion(session_type)
        - In admin interface: When manually marking session completion
        - In API endpoints: When processing attendance completion
        
        Args:
            completed_session_type (str): The session type that was completed ('MA', 'SSP1', etc.)
            
        Returns:
            bool: True if shivir field was updated successfully, False otherwise
        """
        progression_order = ['MA', 'SSP1', 'SSP2', 'HS1', 'HS2']
        
        # Get current shivir level
        current_shivir = self.get_shivir_background_level()
        
        # Enhanced debug logging
        print(f"🔄 [AUTO-UPDATE] Processing shivir field update for {self.name}:")
        print(f"  📊 Current shivir background: {current_shivir}")
        print(f"  🎯 Completed session: {completed_session_type}")
        print(f"  📝 Current shivir field value: '{self.shivir}'")
        
        try:
            # ✅ Enhanced validation: Check if session is in progression order
            if completed_session_type not in progression_order:
                print(f"  ⏭️  [SKIP] {completed_session_type} not in progression order (valid: {', '.join(progression_order)})")
                return False
            
            # ✅ Enhanced validation: Skip Festival sessions
            if completed_session_type == 'FESTIVAL':
                print(f"  🎉 [SKIP] Festival sessions don't affect spiritual progression")
                return False
            
            completed_index = progression_order.index(completed_session_type)
            
            # Handle new users (no current shivir level)
            if current_shivir:
                current_index = progression_order.index(current_shivir)
            else:
                current_index = -1  # New user
                print(f"  👋 New user detected - will set first spiritual level")
            
            # ✅ ENHANCED LOGIC: Update shivir field if completing higher or equal level session
            if completed_index >= current_index:
                old_shivir = self.shivir
                
                # 🚀 AUTOMATIC UPDATE: Set shivir field to completed session type
                self.shivir = completed_session_type
                
                # ✅ Efficient database update: Only update shivir field
                self.save(update_fields=['shivir'])
                
                # 🎉 Success logging with spiritual progression context
                print(f"  ✅ [SUCCESS] Spiritual progression updated!")
                print(f"    📈 Shivir field: '{old_shivir}' → '{completed_session_type}'")
                print(f"    🎯 New eligibility: {', '.join(self.get_eligible_sessions_based_on_shivir())}")
                
                # 📊 Log progression achievement
                if current_index == -1:
                    print(f"    🌟 Achievement: First spiritual level attained!")
                elif completed_index > current_index:
                    levels_advanced = completed_index - current_index
                    print(f"    🚀 Achievement: Advanced {levels_advanced} spiritual level(s)!")
                else:
                    print(f"    🔄 Confirmation: Spiritual level maintained at {completed_session_type}")
                
                return True
            else:
                print(f"  ⚠️  [SKIP] Completed session {completed_session_type} is lower than current level {current_shivir}")
                print(f"    💡 Note: Users can attend lower-level sessions for revision without affecting progression")
                return False
                
        except ValueError as e:
            print(f"  ❌ [ERROR] ValueError in shivir update: {e}")
            print(f"    🔍 Debug: Check if session type '{completed_session_type}' is valid")
            return False
        except Exception as e:
            print(f"  ❌ [ERROR] Unexpected error in shivir field update: {e}")
            print(f"    🔧 Debug: Contact system administrator if this persists")
            return False
    
    # ✅ BONUS FEATURE: Check if user can progress to next level
    def can_progress_to_next_level(self):
        """Check if user can progress to the next spiritual level"""
        progression_order = ['MA', 'SSP1', 'SSP2', 'HS1', 'HS2']
        current_level = self.get_shivir_background_level()
        
        if not current_level:
            return 'MA'  # New users start with MA
        
        try:
            current_index = progression_order.index(current_level)
            if current_index + 1 < len(progression_order):
                return progression_order[current_index + 1]
            else:
                return None  # Already at highest level (HS2)
        except ValueError:
            return 'MA'  # Unknown level, start with MA
    
    # ✅ BONUS FEATURE: Get progression summary
    def get_progression_summary(self):
        """Get comprehensive spiritual progression summary"""
        current_level = self.get_shivir_background_level()
        next_level = self.can_progress_to_next_level()
        eligible = self.get_eligible_sessions_based_on_shivir()
        
        summary = {
            'current_level': current_level or 'New User',
            'next_level': next_level or 'Maximum level achieved',
            'eligible_sessions': eligible,
            'progression_complete': next_level is None
        }
        
        return summary


# 🗄️ SEPARATE REGULAR ATTENDANCE TABLES FOR EACH SESSION TYPE

class MA_Attendance(models.Model):
    """Track daily MA Shivir attendance (5 days total)"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='ma_attendance')
    attendance_date = models.DateField(auto_now_add=True)
    day_number = models.IntegerField(help_text="Day 1, 2, 3, 4, or 5 of MA")
    session_reference = models.ForeignKey('TejgyanSession', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False, help_text="True when all 5 days completed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_ma_attendance'
        verbose_name = "MA Shivir Attendance"
        verbose_name_plural = "MA Shivir Attendances"
        ordering = ['-attendance_date']
        unique_together = [('person', 'attendance_date')]
        indexes = [
            models.Index(fields=['person', 'day_number']),
            models.Index(fields=['attendance_date']),
        ]
    
    def __str__(self):
        status = "✅ Completed" if self.is_completed else f"Day {self.day_number}/5"
        return f"{self.person.name} - MA ({status}) on {self.attendance_date}"
    
    def save(self, *args, **kwargs):
        """Enhanced save method to trigger shivir field update on completion"""
        # Check if this save operation marks the session as completed
        was_completed_before = False
        if self.pk:  # Existing record
            try:
                old_instance = MA_Attendance.objects.get(pk=self.pk)
                was_completed_before = old_instance.is_completed
            except MA_Attendance.DoesNotExist:
                pass
        
        # Save the attendance record
        super().save(*args, **kwargs)
        
        # 🚀 AUTOMATIC SHIVIR UPDATE: If session just completed, update user's shivir field
        if self.is_completed and not was_completed_before:
            print(f"🎉 MA Shivir completed for {self.person.name}! Triggering auto-update...")
            success = self.person.update_shivir_field_on_completion('MA')
            if success:
                print(f"✅ Shivir field automatically updated for {self.person.name}")


class SSP1_Attendance(models.Model):
    """Track daily SSP1 attendance (2 days total)"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='ssp1_attendance')
    attendance_date = models.DateField(auto_now_add=True)
    day_number = models.IntegerField(help_text="Day 1 or 2 of SSP1")
    session_reference = models.ForeignKey('TejgyanSession', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False, help_text="True when both days completed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_ssp1_attendance'
        verbose_name = "SSP1 Attendance"
        verbose_name_plural = "SSP1 Attendances"
        ordering = ['-attendance_date']
        unique_together = [('person', 'attendance_date')]
    
    def __str__(self):
        status = "✅ Completed" if self.is_completed else f"Day {self.day_number}/2"
        return f"{self.person.name} - SSP1 ({status}) on {self.attendance_date}"
    
    def save(self, *args, **kwargs):
        """Enhanced save method to trigger shivir field update on completion"""
        was_completed_before = False
        if self.pk:
            try:
                old_instance = SSP1_Attendance.objects.get(pk=self.pk)
                was_completed_before = old_instance.is_completed
            except SSP1_Attendance.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # 🚀 AUTOMATIC SHIVIR UPDATE
        if self.is_completed and not was_completed_before:
            print(f"🎉 SSP1 completed for {self.person.name}! Triggering auto-update...")
            self.person.update_shivir_field_on_completion('SSP1')


class SSP2_Attendance(models.Model):
    """Track daily SSP2 attendance (2 days total)"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='ssp2_attendance')
    attendance_date = models.DateField(auto_now_add=True)
    day_number = models.IntegerField(help_text="Day 1 or 2 of SSP2")
    session_reference = models.ForeignKey('TejgyanSession', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False, help_text="True when both days completed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_ssp2_attendance'
        verbose_name = "SSP2 Attendance"
        verbose_name_plural = "SSP2 Attendances"
        ordering = ['-attendance_date']
        unique_together = [('person', 'attendance_date')]
    
    def __str__(self):
        status = "✅ Completed" if self.is_completed else f"Day {self.day_number}/2"
        return f"{self.person.name} - SSP2 ({status}) on {self.attendance_date}"
    
    def save(self, *args, **kwargs):
        """Enhanced save method to trigger shivir field update on completion"""
        was_completed_before = False
        if self.pk:
            try:
                old_instance = SSP2_Attendance.objects.get(pk=self.pk)
                was_completed_before = old_instance.is_completed
            except SSP2_Attendance.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # 🚀 AUTOMATIC SHIVIR UPDATE
        if self.is_completed and not was_completed_before:
            print(f"🎉 SSP2 completed for {self.person.name}! Triggering auto-update...")
            self.person.update_shivir_field_on_completion('SSP2')


class HS1_Attendance(models.Model):
    """Track daily Higher Shivir 1 attendance (2 days total)"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='hs1_attendance')
    attendance_date = models.DateField(auto_now_add=True)
    day_number = models.IntegerField(help_text="Day 1 or 2 of HS1")
    session_reference = models.ForeignKey('TejgyanSession', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False, help_text="True when both days completed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_hs1_attendance'
        verbose_name = "Higher Shivir 1 Attendance"
        verbose_name_plural = "Higher Shivir 1 Attendances"
        ordering = ['-attendance_date']
        unique_together = [('person', 'attendance_date')]
    
    def __str__(self):
        status = "✅ Completed" if self.is_completed else f"Day {self.day_number}/2"
        return f"{self.person.name} - HS1 ({status}) on {self.attendance_date}"
    
    def save(self, *args, **kwargs):
        """Enhanced save method to trigger shivir field update on completion"""
        was_completed_before = False
        if self.pk:
            try:
                old_instance = HS1_Attendance.objects.get(pk=self.pk)
                was_completed_before = old_instance.is_completed
            except HS1_Attendance.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # 🚀 AUTOMATIC SHIVIR UPDATE
        if self.is_completed and not was_completed_before:
            print(f"🎉 HS1 completed for {self.person.name}! Triggering auto-update...")
            self.person.update_shivir_field_on_completion('HS1')


class HS2_Attendance(models.Model):
    """Track daily Higher Shivir 2 attendance (2 days total)"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='hs2_attendance')
    attendance_date = models.DateField(auto_now_add=True)
    day_number = models.IntegerField(help_text="Day 1 or 2 of HS2")
    session_reference = models.ForeignKey('TejgyanSession', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False, help_text="True when both days completed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_hs2_attendance'
        verbose_name = "Higher Shivir 2 Attendance"
        verbose_name_plural = "Higher Shivir 2 Attendances"
        ordering = ['-attendance_date']
        unique_together = [('person', 'attendance_date')]
    
    def __str__(self):
        status = "✅ Completed" if self.is_completed else f"Day {self.day_number}/2"
        return f"{self.person.name} - HS2 ({status}) on {self.attendance_date}"
    
    def save(self, *args, **kwargs):
        """Enhanced save method to trigger shivir field update on completion"""
        was_completed_before = False
        if self.pk:
            try:
                old_instance = HS2_Attendance.objects.get(pk=self.pk)
                was_completed_before = old_instance.is_completed
            except HS2_Attendance.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # 🚀 AUTOMATIC SHIVIR UPDATE
        if self.is_completed and not was_completed_before:
            print(f"🎉 HS2 completed for {self.person.name}! Triggering auto-update...")
            self.person.update_shivir_field_on_completion('HS2')


# 🔄 SEPARATE REPEATER TABLES FOR EACH SESSION TYPE

class MA_Repeaters(models.Model):
    """Track MA Shivir repeat attendance with dynamic days gap"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='ma_repeaters')
    previous_attendance_date = models.DateField(help_text="When they last completed MA")
    repeat_attendance_date = models.DateField(auto_now_add=True, help_text="Today's repeat attendance")
    days_gap = models.IntegerField(help_text="Days between last completion and repeat")
    repeat_count = models.IntegerField(default=1, help_text="1st repeat, 2nd repeat, etc.")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_ma_repeaters'
        verbose_name = "MA Shivir Repeater"
        verbose_name_plural = "MA Shivir Repeaters"
        ordering = ['-repeat_attendance_date']
        indexes = [
            models.Index(fields=['person', 'repeat_attendance_date']),
        ]
    
    def __str__(self):
        return f"{self.person.name} - MA repeat #{self.repeat_count} after {self.days_gap} days"
    
    def get_gap_display(self):
        """Get user-friendly gap display"""
        if self.days_gap == 1:
            return "1 day"
        elif self.days_gap < 7:
            return f"{self.days_gap} days"
        elif self.days_gap < 30:
            weeks = self.days_gap // 7
            return f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = self.days_gap // 30
            return f"{months} month{'s' if months > 1 else ''}"


class SSP1_Repeaters(models.Model):
    """Track SSP1 repeat attendance with dynamic days gap"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='ssp1_repeaters')
    previous_attendance_date = models.DateField(help_text="When they last completed SSP1")
    repeat_attendance_date = models.DateField(auto_now_add=True)
    days_gap = models.IntegerField()
    repeat_count = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_ssp1_repeaters'
        verbose_name = "SSP1 Repeater"
        verbose_name_plural = "SSP1 Repeaters"
        ordering = ['-repeat_attendance_date']
    
    def __str__(self):
        return f"{self.person.name} - SSP1 repeat #{self.repeat_count} after {self.days_gap} days"
    
    def get_gap_display(self):
        if self.days_gap == 1:
            return "1 day"
        elif self.days_gap < 7:
            return f"{self.days_gap} days"
        elif self.days_gap < 30:
            weeks = self.days_gap // 7
            return f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = self.days_gap // 30
            return f"{months} month{'s' if months > 1 else ''}"


class SSP2_Repeaters(models.Model):
    """Track SSP2 repeat attendance with dynamic days gap"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='ssp2_repeaters')
    previous_attendance_date = models.DateField(help_text="When they last completed SSP2")
    repeat_attendance_date = models.DateField(auto_now_add=True)
    days_gap = models.IntegerField()
    repeat_count = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_ssp2_repeaters'
        verbose_name = "SSP2 Repeater"
        verbose_name_plural = "SSP2 Repeaters"
        ordering = ['-repeat_attendance_date']
    
    def __str__(self):
        return f"{self.person.name} - SSP2 repeat #{self.repeat_count} after {self.days_gap} days"
    
    def get_gap_display(self):
        if self.days_gap == 1:
            return "1 day"
        elif self.days_gap < 7:
            return f"{self.days_gap} days"
        elif self.days_gap < 30:
            weeks = self.days_gap // 7
            return f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = self.days_gap // 30
            return f"{months} month{'s' if months > 1 else ''}"


class HS1_Repeaters(models.Model):
    """Track Higher Shivir 1 repeat attendance with dynamic days gap"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='hs1_repeaters')
    previous_attendance_date = models.DateField(help_text="When they last completed HS1")
    repeat_attendance_date = models.DateField(auto_now_add=True)
    days_gap = models.IntegerField()
    repeat_count = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_hs1_repeaters'
        verbose_name = "Higher Shivir 1 Repeater"
        verbose_name_plural = "Higher Shivir 1 Repeaters"
        ordering = ['-repeat_attendance_date']
    
    def __str__(self):
        return f"{self.person.name} - HS1 repeat #{self.repeat_count} after {self.days_gap} days"
    
    def get_gap_display(self):
        if self.days_gap == 1:
            return "1 day"
        elif self.days_gap < 7:
            return f"{self.days_gap} days"
        elif self.days_gap < 30:
            weeks = self.days_gap // 7
            return f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = self.days_gap // 30
            return f"{months} month{'s' if months > 1 else ''}"


class HS2_Repeaters(models.Model):
    """Track Higher Shivir 2 repeat attendance with dynamic days gap"""
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE, related_name='hs2_repeaters')
    previous_attendance_date = models.DateField(help_text="When they last completed HS2")
    repeat_attendance_date = models.DateField(auto_now_add=True)
    days_gap = models.IntegerField()
    repeat_count = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faceapp_hs2_repeaters'
        verbose_name = "Higher Shivir 2 Repeater"
        verbose_name_plural = "Higher Shivir 2 Repeaters"
        ordering = ['-repeat_attendance_date']
    
    def __str__(self):
        return f"{self.person.name} - HS2 repeat #{self.repeat_count} after {self.days_gap} days"
    
    def get_gap_display(self):
        if self.days_gap == 1:
            return "1 day"
        elif self.days_gap < 7:
            return f"{self.days_gap} days"
        elif self.days_gap < 30:
            weeks = self.days_gap // 7
            return f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = self.days_gap // 30
            return f"{months} month{'s' if months > 1 else ''}"


# TejgyanSession Model for Sirshree's Session Management (Enhanced)
class TejgyanSession(models.Model):
    SESSION_CHOICES = [
        ('MA', 'MA Shivir'),
        ('SSP1', 'SSP1 (MTS 1)'),
        ('SSP2', 'SSP2 (MTS 2)'),
        ('HS1', 'Higher Shivir 1'),
        ('HS2', 'Higher Shivir 2'),
        ('FESTIVAL', 'Festival/Open Session'),
    ]
    
    session_name = models.CharField(
        max_length=100, 
        help_text="e.g., 'Morning MA Shivir', 'Evening SSP1', 'Diwali Festival Session'"
    )
    session_type = models.CharField(
        max_length=20, 
        choices=SESSION_CHOICES,
        help_text="Select the type of session conducted by Tejgyan Foundation"
    )
    session_date = models.DateField(
        default=timezone.now,
        help_text="Date when this session is/was conducted"
    )
    conducted_by = models.CharField(
        max_length=100, 
        default="Sirshree",
        help_text="Name of the person conducting the session"
    )
    
    # KEY FIELD: Only one session can be active at a time
    is_active = models.BooleanField(
        default=False, 
        help_text="Check this to make it today's active session for face recognition attendance marking. Only ONE session can be active at a time."
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        active_status = " [ACTIVE]" if self.is_active else ""
        return f"{self.session_name} ({self.get_session_type_display()}){active_status}"
    
    def save(self, *args, **kwargs):
        """Custom save method to ensure only one session is active at a time"""
        if self.is_active:
            # Deactivate all other sessions before saving this as active
            TejgyanSession.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-session_date', '-created_at']
        verbose_name = "Tejgyan Session"
        verbose_name_plural = "Tejgyan Sessions"
        
    @classmethod
    def get_active_session(cls):
        """Get the currently active session for face recognition"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # Fix multiple active sessions by keeping only the latest
            active_sessions = cls.objects.filter(is_active=True).order_by('-created_at')
            latest_session = active_sessions.first()
            active_sessions.exclude(pk=latest_session.pk).update(is_active=False)
            return latest_session
    
    def get_eligible_users_count(self):
        """Get count of users eligible for this session type based on shivir field"""
        eligible_count = 0
        for person in KnownPerson.objects.filter(is_active=True):
            if person.is_eligible_for_session(self.session_type):
                eligible_count += 1
        return eligible_count
    
    def get_prerequisite_session(self):
        """Get the prerequisite session for this session type"""
        prerequisites = {
            'MA': None,
            'SSP1': 'MA',
            'SSP2': 'SSP1', 
            'HS1': 'SSP2',
            'HS2': 'HS1',
            'FESTIVAL': None
        }
        return prerequisites.get(self.session_type)
    
    def get_session_duration(self):
        """Get duration for this session type"""
        durations = {
            'MA': 5,
            'SSP1': 2,
            'SSP2': 2,
            'HS1': 2,
            'HS2': 2,
            'FESTIVAL': 1
        }
        return durations.get(self.session_type, 1)


# Updated Attendance Model with NULL Session Support (Enhanced)
class Attendance(models.Model):
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE)
    
    # Allow NULL sessions until admin selects one
    session = models.ForeignKey(
        'TejgyanSession', 
        on_delete=models.CASCADE, 
        null=True,           
        blank=True,          
        help_text="Session will be NULL until admin selects an active session"
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional metadata for better tracking
    marked_by_system = models.BooleanField(
        default=True, 
        help_text="True if marked by face recognition, False if manually added"
    )

    def __str__(self):
        # Handle both NULL and active sessions gracefully
        ist = pytz.timezone('Asia/Kolkata')
        local_time = self.timestamp.astimezone(ist)
        
        if self.session:
            return f"{self.person.name} - {self.session.session_name} at {local_time.strftime('%Y-%m-%d %H:%M:%S IST')}"
        else:
            return f"{self.person.name} attended at {local_time.strftime('%Y-%m-%d %H:%M:%S IST')} (General attendance)"
    
    class Meta:
        ordering = ['-timestamp']  # Show newest attendance first
        
        # Constraint only applies when session is NOT NULL
        constraints = [
            models.UniqueConstraint(
                fields=['person', 'session'],
                condition=models.Q(session__isnull=False),
                name='unique_person_session_daily_attendance'
            )
        ]
    
    def get_session_type_display(self):
        """Get human-readable session type"""
        if self.session:
            return self.session.get_session_type_display()
        return "General Attendance"
    
    def get_ist_time(self):
        """Get attendance time in IST"""
        ist = pytz.timezone('Asia/Kolkata')
        return self.timestamp.astimezone(ist)
    
    def is_valid_attendance(self):
        """Check if this attendance was marked for a session the person was eligible for based on shivir field"""
        if not self.session:
            return True  # General attendance is always valid
        
        return self.person.is_eligible_for_session(self.session.session_type)
    
    def get_attendance_validity_display(self):
        """Get display text for attendance validity"""
        if self.is_valid_attendance():
            return "Valid"
        else:
            return "Invalid (Not Eligible)"
