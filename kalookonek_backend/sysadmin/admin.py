from django.contrib import admin
from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'published_at', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'body')
    actions = ['publish_announcements']

    def publish_announcements(self, request, queryset):
        for announcement in queryset:
            announcement.publish()
    publish_announcements.short_description = 'Publish selected announcements'