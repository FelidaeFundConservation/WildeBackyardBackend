from django.urls import path, re_path

from siteapps.socialmedia.views import (
    CreateCommentView,
    CreatePostView,
    GetPostResponsesAuthenticatedView,
    GetPostResponsesNoAuthView,
    GetRecentPostsView,
    LikePostView,
)

urlpatterns = [
    path("api/comments/create/", CreateCommentView.as_view(), name="create_comment"),
    path("api/posts/create/", CreatePostView.as_view(), name="create_post"),
    path("api/posts/like/", LikePostView.as_view(), name="like_post"),
    re_path(r"^api/feed/get/$", GetRecentPostsView.as_view(), name="get_posts"),
    path("api/posts/responses/get/noauth", GetPostResponsesNoAuthView.as_view(), name="get_post_responses_noauth"),
    path("api/posts/responses/get/auth", GetPostResponsesAuthenticatedView.as_view(), name="get_post_responses_auth"),
]
