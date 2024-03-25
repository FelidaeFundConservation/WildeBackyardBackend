from django.urls import path

from siteapps.socialmedia.views import CreatePostView, GetRecentPostsView

urlpatterns = [
    path("api/post/create/", CreatePostView.as_view(), name="create_post"),
    path("api/feed/get_recent_posts/", GetRecentPostsView.as_view(), name="get_recent_posts"),
]
