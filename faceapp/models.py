# faceapp/models.py
from django.db import models
from .storage import OverwriteStorage
import pytz  # ✅ ADDED: For timezone conversion
from django.utils import timezone  # ✅ ADDED: For timezone handling

class KnownPerson(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=100)
    shivir = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default=False)
    image = models.ImageField(upload_to='known_faces/',storage= OverwriteStorage(), null=True, blank=True) 
    encoding = models.BinaryField(blank=True, null=True)
    
    # Blacklist feature
    is_blacklisted = models.BooleanField(default=False, help_text="If checked, attendance will not be marked for this person")
    blacklisted_reason = models.CharField(max_length=200, blank=True, null=True, help_text="Reason for blacklisting")
    blacklisted_date = models.DateTimeField(blank=True, null=True, help_text="Date when person was blacklisted")
    
    # ✅ NEW: Activation/Deactivation feature
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

# ✅ NEW: TejgyanSession Model for Sirshree's Session Management
class TejgyanSession(models.Model):
    SESSION_CHOICES = [
        ('MA', 'MA Shivir (MA)'),
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
    
    # ✅ KEY FIELD: Only one session can be active at a time
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
        """
        Custom save method to ensure only one session is active at a time
        """
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
        """
        Get the currently active session for face recognition
        """
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

# ✅ ENHANCED: Updated Attendance Model with NULL Session Support
class Attendance(models.Model):
    person = models.ForeignKey('KnownPerson', on_delete=models.CASCADE)
    
    # ✅ UPDATED: Allow NULL sessions until admin selects one
    session = models.ForeignKey(
        'TejgyanSession', 
        on_delete=models.CASCADE, 
        null=True,           # ✅ KEEP: Allow NULL values
        blank=True,          # ✅ KEEP: Allow empty in forms
        help_text="Session will be NULL until admin selects an active session"
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # ✅ Additional metadata for better tracking
    marked_by_system = models.BooleanField(
        default=True, 
        help_text="True if marked by face recognition, False if manually added"
    )

    def __str__(self):
        # ✅ ENHANCED: Handle both NULL and active sessions gracefully
        ist = pytz.timezone('Asia/Kolkata')
        local_time = self.timestamp.astimezone(ist)
        
        if self.session:
            return f"{self.person.name} - {self.session.session_name} at {local_time.strftime('%Y-%m-%d %H:%M:%S IST')}"
        else:
            # ✅ UPDATED: Better message for NULL sessions
            return f"{self.person.name} attended at {local_time.strftime('%Y-%m-%d %H:%M:%S IST')} (General attendance)"
    
    class Meta:
        ordering = ['-timestamp']  # Show newest attendance first
        
        # ✅ UPDATED: Constraint only applies when session is NOT NULL
        constraints = [
            models.UniqueConstraint(
                fields=['person', 'session'],
                condition=models.Q(session__isnull=False),  # ✅ FIXED: Only when session is NOT NULL
                name='unique_person_session_daily_attendance'
            )
        ]
    
    def get_session_type_display(self):
        """Get human-readable session type"""
        if self.session:
            return self.session.get_session_type_display()
        return "General Attendance"  # ✅ UPDATED: Better message for NULL sessions
    
    def get_ist_time(self):
        """Get attendance time in IST"""
        ist = pytz.timezone('Asia/Kolkata')
        return self.timestamp.astimezone(ist)
