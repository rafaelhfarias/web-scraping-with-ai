from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from django.db.models import Q
from .models import Link, Crawler  
from .serializers import (
    LinkSerializer, CrawlerSerializer, MessageSerializer, LoginSerializer
)
from .services import WebScraper, get_active_crawlers, stop_crawler, stop_all_crawlers
import threading
import uuid



class LinkViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LinkSerializer
    permission_classes = [IsAuthenticated]
    
    # Simplify the retrieve schema
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='Link ID'
            )
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    def get_queryset(self):
        # Filter links by the user's crawlers
        queryset = Link.objects.filter(crawler__user=self.request.user).order_by('-relevance_score')
        
        # Apply filters if provided
        keyword = self.request.query_params.get('keyword')
        link_type = self.request.query_params.get('type')
        min_relevance = self.request.query_params.get('min_relevance')
        
        if keyword:
            queryset = queryset.filter(keywords=keyword)
        
        if link_type:
            queryset = queryset.filter(type=link_type)
            
        if min_relevance:
            try:
                min_relevance = float(min_relevance)
                queryset = queryset.filter(relevance_score__gte=min_relevance)
            except ValueError:
                pass
                
        return queryset
    
    # Removing start_crawl from LinkViewSet

class StartCrawlView(generics.GenericAPIView):
    serializer_class = LinkSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        operation_id='start_crawl',
        description='Start a new web crawling task',
        request=LinkSerializer,
        responses={
            202: MessageSerializer,
            400: MessageSerializer
        }
    )
    def post(self, request):
        url = request.data.get('url')
        keyword = request.data.get('keyword')
        depth = int(request.data.get('depth', 3))
        workers = int(request.data.get('workers', 50))
        
        if not url or not keyword:
            return Response(
                {"error": "URL and keyword are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Start crawling in a background thread
        def crawl_task():
            scraper = WebScraper(keyword=keyword, user=request.user)
            scraper.crawl(url, max_depth=depth, max_workers=workers)
            
        thread = threading.Thread(target=crawl_task)
        thread.daemon = True
        thread.start()
        
        return Response(
            {"message": f"Crawling started for {url} with keyword '{keyword}'"},
            status=status.HTTP_202_ACCEPTED
        )

class ListCrawlersView(generics.ListAPIView):
    serializer_class = CrawlerSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        operation_id='list_crawlers',
        description='List all crawlers for the authenticated user',
        parameters=[
            OpenApiParameter(name='active', description='Filter by active crawlers', required=False, type=OpenApiTypes.BOOL, default=True)
        ],
        responses={200: CrawlerSerializer(many=True)}
    )
    def get_queryset(self):
        active = self.request.query_params.get('active', 'true').lower() == 'true'
        
        if active:
            return Crawler.objects.filter(user=self.request.user, is_running=True)
        else:
            return Crawler.objects.filter(user=self.request.user)

class StopCrawlerView(generics.GenericAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: MessageSerializer, 404: MessageSerializer}
    )
    def post(self, request, crawler_id):
        try:
            # Convert string to UUID
            crawler_id = uuid.UUID(crawler_id)
            crawler = Crawler.objects.filter(id=crawler_id, user=request.user).first()
            
            if not crawler:
                return Response(
                    {"error": f"Crawler {crawler_id} not found or not owned by you"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            crawler.is_running = False
            crawler.save()
            
            return Response({"message": f"Crawler {crawler_id} stopped successfully"})
            
        except ValueError:
            return Response(
                {"error": "Invalid crawler ID format"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Error stopping crawler: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StopAllCrawlersView(generics.GenericAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: MessageSerializer}
    )
    def post(self, request):
        """Stop all active crawlers for the authenticated user"""
        # Modify the service to only stop crawlers for the current user
        user_crawlers = Crawler.objects.filter(user=request.user, is_running=True)
        for crawler in user_crawlers:
            stop_crawler(crawler.id)
        
        return Response({"message": "All your crawlers are stopping"})

class LoginView(generics.GenericAPIView):
    permission_classes = []
    serializer_class = LoginSerializer
    
    @extend_schema(
        responses={200: {"type": "object", "properties": {
            "refresh": {"type": "string"},
            "access": {"type": "string"}
        }}}
    )
    def post(self, request):
        """Login and get JWT tokens"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            return Response(
                {"error": "Invalid credentials"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

class TestView(APIView):
    permission_classes = []
    
    def get(self, request):
        return Response({"message": "Test endpoint is working"})
