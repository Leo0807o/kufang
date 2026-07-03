def user_group(request):
    """Add user_group to template context from middleware."""
    return {
        'user_group': getattr(request, 'user_group', None),
        'is_admin': getattr(request, 'is_admin', False),
    }
