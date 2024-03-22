from django.urls import path

from siteapps.socialmedia.views import CreatePostView

urlpatterns = [
    path("api/post/create/", CreatePostView.as_view(), name="create_post"),
]
