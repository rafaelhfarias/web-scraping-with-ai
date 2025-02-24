from django.db import models
from django.contrib.auth.models import User
import uuid

class Crawler(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField()
    keyword = models.CharField(max_length=100)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_running = models.BooleanField(default=True)
    max_depth = models.IntegerField(default=3)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crawlers')
    
    def __str__(self):
        return f"Crawler {self.id} - {self.url} - {self.keyword}"
    
    class Meta:
        ordering = ['-start_time']

class Link(models.Model):
    url = models.URLField()
    type = models.CharField(max_length=50)
    relevance_score = models.FloatField()
    keywords = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    crawler = models.ForeignKey(Crawler, on_delete=models.CASCADE, related_name='links')
    
    def __str__(self):
        return f"{self.url} ({self.type})"
    
    class Meta:
        indexes = [
            models.Index(fields=['keywords']),
            models.Index(fields=['type']),
            models.Index(fields=['relevance_score']),
        ]
        unique_together = ['url', 'crawler']
