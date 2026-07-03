from django.http import HttpResponseForbidden
from functools import wraps
from .models import Inventory


def require_group_owner(view_func):
    """Decorator: verify request.user.group == record.group for write operations.
    Must be used on views that receive an `inventory_id` kwarg.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        inventory_id = kwargs.get('inventory_id') or kwargs.get('pk')
        if inventory_id:
            try:
                item = Inventory.objects.get(pk=inventory_id)
            except Inventory.DoesNotExist:
                return HttpResponseForbidden('备件不存在')
            if item.group != request.user_group:
                return HttpResponseForbidden('您无权操作其他组的备件')
        return view_func(request, *args, **kwargs)
    return wrapper
