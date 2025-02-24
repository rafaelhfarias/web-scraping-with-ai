from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LinkViewSet, 
    ListCrawlersView, 
    StopCrawlerView, 
    StopAllCrawlersView,
    LoginView,
    TestView,
    StartCrawlView  # Add the new view
)
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'links', LinkViewSet, basename='link')

urlpatterns = [
    path('', include(router.urls)),
    path('crawlers/', ListCrawlersView.as_view(), name='list-crawlers'),
    path('crawlers/start/', StartCrawlView.as_view(), name='start-crawler'),  # Add new endpoint
    path('crawlers/stop/<uuid:crawler_id>/', StopCrawlerView.as_view(), name='stop-crawler'),
    path('crawlers/stop-all/', StopAllCrawlersView.as_view(), name='stop-all-crawlers'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('test/', TestView.as_view(), name='test-view'),
]