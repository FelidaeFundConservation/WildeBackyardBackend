from django.urls import path

from siteapps.socialmedia.views import (
    CreatePostView,
    GetRecentPostsAuthenticatedView,
    GetRecentPostsNoAuthView,
    LikePostView,
)

urlpatterns = [
    path("api/posts/create/", CreatePostView.as_view(), name="create_post"),
    path("api/posts/like/", LikePostView.as_view(), name="like_post"),
    path("api/feed/get/auth", GetRecentPostsAuthenticatedView.as_view(), name="get_posts_authenticated"),
    path("api/feed/get/noauth", GetRecentPostsNoAuthView.as_view(), name="get_posts_no_auth"),
]
