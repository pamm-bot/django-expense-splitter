from rest_framework.permissions import BasePermission


class IsGroupMember(BasePermission):
    """Grants access only to members of the group referenced by the URL
    (`group_pk` for nested routes, or the object itself for group routes)."""

    message = "You are not a member of this group."

    def has_permission(self, request, view):
        group = view.get_group()
        return group.members.filter(pk=request.user.pk).exists()

    def has_object_permission(self, request, view, obj):
        group = obj if obj.__class__.__name__ == "Group" else obj.group
        return group.members.filter(pk=request.user.pk).exists()
