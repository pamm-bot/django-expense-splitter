from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Login / register — the JS checks localStorage for a token and
    redirects straight to the group list if the visitor is already signed in."""

    template_name = "frontend/home.html"


class GroupsView(TemplateView):
    template_name = "frontend/groups.html"


class GroupDetailView(TemplateView):
    template_name = "frontend/group_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["group_id"] = kwargs["group_id"]
        return context
