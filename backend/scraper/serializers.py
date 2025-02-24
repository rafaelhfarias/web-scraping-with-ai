from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Link, Crawler

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class CrawlerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crawler
        fields = ['id', 'url', 'keyword', 'start_time', 'end_time', 'is_running', 'max_depth', 'user']
        read_only_fields = ['id'] 


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = ['id', 'url', 'type', 'relevance_score', 'keywords', 'metadata', 'created_at', 'updated_at', 'crawler']

# Add the missing serializers
class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class CrawlerIdSerializer(serializers.Serializer):
    crawler_id = serializers.CharField()