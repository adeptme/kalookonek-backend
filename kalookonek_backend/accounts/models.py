from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    phone_number = models.CharField(max_length=20, blank=True)
    is_approved = models.BooleanField(default=False)
    profile_picture = models.TextField(blank=True, null=True)

    # Extended demographic fields
    barangay = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True)  # Date of Birth (YYYY-MM-DD)

    # Internal field: links this profile to the Supabase Auth user (never exposed to frontend)
    supabase_uid = models.UUIDField(unique=True, null=True, blank=True)

    # Human-readable frontend ID in YYYY-NNN format (e.g. 2026-001)
    # This is the ID used for search and display — not the Supabase UUID
    display_id = models.CharField(max_length=20, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-calculate age from DOB if it exists
        if self.dob:
            from datetime import date
            today = date.today()
            self.age = today.year - self.dob.year - (
                (today.month, today.day) < (self.dob.month, self.dob.day)
            )

        # Auto-generate display_id if not already set
        if not self.display_id:
            year = timezone.now().year
            count = UserProfile.objects.filter(created_at__year=year).count() + 1
            self.display_id = f"{year}-{count:03d}"
        super().save(*args, **kwargs)

    @property
    def calculated_age(self):
        """Returns the real-time age based on DOB."""
        if not self.dob:
            return self.age
        from datetime import date
        today = date.today()
        return today.year - self.dob.year - (
            (today.month, today.day) < (self.dob.month, self.dob.day)
        )

    def __str__(self):
        return f"{self.display_id} — {self.user.get_full_name()} ({self.role})"

    @property
    def is_staff_member(self):
        return self.role in ('staff', 'admin')