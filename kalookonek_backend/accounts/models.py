from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')
    phone_number = models.CharField(max_length=20, blank=True)
    is_approved = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

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
        # Auto-generate display_id if not already set
        if not self.display_id:
            year = timezone.now().year
            count = UserProfile.objects.filter(created_at__year=year).count() + 1
            self.display_id = f"{year}-{count:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.display_id} — {self.user.get_full_name()} ({self.role})"

    @property
    def is_staff_member(self):
        return self.role in ('staff', 'admin')