from django.contrib.auth.models import Group


class UserGroupMiddleware:
    """Inject request.user_group for every authenticated request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            request.user_group = profile.group if profile else None
            request.is_admin = (
                profile is not None
                and profile.group is not None
                and profile.group.name == '管理员'
            )
        else:
            request.user_group = None
            request.is_admin = False
        return self.get_response(request)
