from django.core.management.base import BaseCommand
from django.utils import timezone
from kalookonek_backend.accounts.models import UserProfile
from django.db import transaction

class Command(BaseCommand):
    help = 'Archives patient accounts that have been inactive for 90 days or more.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the script without actually saving changes to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        archived_count = 0
        already_archived_count = 0

        self.stdout.write(self.style.NOTICE(f"Starting archiving process. Dry run: {dry_run}"))

        # We only care about patients
        patient_profiles = UserProfile.objects.filter(role='patient').select_related('user')
        
        with transaction.atomic():
            for profile in patient_profiles:
                user = profile.user
                last_activity = user.last_login or profile.created_at
                days_inactive = (now - last_activity).days

                if days_inactive >= 90:
                    if profile.status != 'archived':
                        profile.status = 'archived'
                        if not dry_run:
                            profile.save(update_fields=['status'])
                        archived_count += 1
                        self.stdout.write(f"Archiving user {user.email} (Inactive for {days_inactive} days)")
                    else:
                        already_archived_count += 1

        self.stdout.write(self.style.SUCCESS(f"Process complete."))
        self.stdout.write(self.style.SUCCESS(f"Newly archived: {archived_count}"))
        self.stdout.write(self.style.SUCCESS(f"Already archived: {already_archived_count}"))
