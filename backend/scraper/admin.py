from django.contrib import admin
from .models import Link

@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('url', 'type', 'relevance_score', 'keywords')
    list_filter = ('type', 'keywords')
    search_fields = ('url', 'metadata')
