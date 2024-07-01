from django.urls import path, re_path

from siteapps.socialmedia.views import (
    CreateCommentView,
    CreateInappropriateContentReportView,
    CreatePostView,
    GetNextReportedContentView,
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
    path("api/posts/report_content/", CreateInappropriateContentReportView.as_view(), name="report_content"),
    path("api/posts/review_reports/", GetNextReportedContentView.as_view(), name="get_reported_content"),
]
