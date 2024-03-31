from django.urls import path

from siteapps.socialmedia.views import CreatePostView, GetRecentPostsView, LikePostView

urlpatterns = [
    path("api/posts/create/", CreatePostView.as_view(), name="create_post"),
    path("api/posts/like/", LikePostView.as_view(), name="like_post"),
    path("api/feed/get/", GetRecentPostsView.as_view(), name="get_posts"),
]
