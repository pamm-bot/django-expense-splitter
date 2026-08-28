from django.test import TestCase
from django.urls import reverse


class FrontendPagesTest(TestCase):
    """These pages are static shells that fetch everything from the API
    client-side, so this only checks they render without error."""

    def test_home_page_renders(self):
        response = self.client.get(reverse("frontend:home"))
        self.assertEqual(response.status_code, 200)

    def test_groups_page_renders(self):
        response = self.client.get(reverse("frontend:groups"))
        self.assertEqual(response.status_code, 200)

    def test_group_detail_page_renders(self):
        response = self.client.get(reverse("frontend:group-detail", args=[1]))
        self.assertEqual(response.status_code, 200)
