import json

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, force_authenticate

from siteapps.users.models import User


# Create your tests here.
class UsersAPITestCase(TestCase):
    def setUp(self):
        # Setup a test account
        test_email = "wildebackyard@fakeemail.com"
        test_password = "fakepassword"

        self.user = User.objects.create(email=test_email)
        self.user.set_password(test_password)
        self.user.is_superuser = True
        self.user.save()

        self.client = APIClient()
        self.client.login(email=test_email, password=test_password)

        # Get the auth token from the test account
        login_response = self.client.post(
            "/users/login/", {"email": test_email, "password": test_password}, format="json"
        )

        token = json.loads(login_response.content)["key"]
        headers = self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

    def test_get_profile(self):
        response = self.client.get("/users/profile/", format="json")

        # print(response.content)

    def test_change_username(self):
        new_username = "MyName1234"

        response = self.client.post("/users/profile/change_username", {"newUsername": new_username}, format="json")

        user = User.objects.get(id=self.user.id)

        self.assertEqual(user.name, new_username)

    def test_username_too_short(self):
        new_username = "sh"

        response = self.client.post("/users/profile/change_username", {"newUsername": new_username}, format="json")
        # print(response.content)
        self.assertEqual(response.status_code, 400)

    def test_delete_account(self):
        new_username = "DeleteMyAccount"

        response = self.client.post("/users/profile/change_username", {"newUsername": new_username}, format="json")

        user = User.objects.get(id=self.user.id)

        response2 = self.client.post("/users/delete_account", {"confirmation_string": new_username}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(name=new_username).exists(), False)
