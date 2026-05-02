from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default='patient')
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', blank=True, null=True)

    # --- NEW FIELDS FOR PATIENT DIRECTORY & STAFF MANAGEMENT ---
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, blank=True)
    barangay = models.CharField(
        max_length=100, blank=True, default='Brgy. 171')

    # default=False ensures staff appear in your "Pending" list on the dashboard
    is_approved = models.BooleanField(default=False)
    # ----------------------------------------------------------

    # Internal field: links this profile to the Supabase Auth user
    supabase_uid = models.UUIDField(unique=True, null=True, blank=True)

    # Human-readable frontend ID (e.g., 2026-001)
    display_id = models.CharField(max_length=20, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # 1. Auto-generate display_id if not already set
        if not self.display_id:
            year = timezone.now().year
            count = UserProfile.objects.filter(
                created_at__year=year).count() + 1
            self.display_id = f"{year}-{count:03d}"

        # 2. Logic: Patients don't need approval, but Staff/Admin do
        # This checks if it's a new record (no ID yet) to avoid overwriting manual changes later
        if not self.pk and self.role == 'patient':
            self.is_approved = True

        super().save(*args, **kwargs)

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{self.display_id} — {name} ({self.role})"

    @property
    def is_staff_member(self):
        return self.role in ('staff', 'admin')
