from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
from .models import UserProfile


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, '用户名或密码错误')

    # Get all users for the quick-login panel
    users = User.objects.filter(is_active=True).select_related('profile__group')
    return render(request, 'login.html', {'users': users})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


def _require_admin(request):
    """Return True if user is admin, else redirect to dashboard with error."""
    if not getattr(request, 'is_admin', False):
        messages.error(request, '您没有管理员权限')
        return redirect('dashboard')
    return None


# ==================== USER MANAGEMENT ====================

@login_required
def user_list(request):
    """Admin-only: list all users."""
    redirect_resp = _require_admin(request)
    if redirect_resp:
        return redirect_resp

    users = User.objects.filter(is_active=True).select_related('profile__group').order_by('username')
    groups = Group.objects.all().order_by('name')
    return render(request, 'user_list.html', {
        'section': 'users',
        'users': users,
        'groups': groups,
    })


@login_required
def user_create(request):
    """Admin-only: create a new user."""
    redirect_resp = _require_admin(request)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        group_id = request.POST.get('group', '')
        phone = request.POST.get('phone', '').strip()
        employee_id = request.POST.get('employee_id', '').strip()

        if not username or not password:
            messages.error(request, '用户名和密码为必填项')
            return redirect('user_list')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'用户名「{username}」已存在')
            return redirect('user_list')

        user = User.objects.create_user(
            username=username, password=password,
            first_name=first_name, is_staff=True,
        )
        group = Group.objects.get(pk=group_id) if group_id else None
        UserProfile.objects.create(
            user=user, group=group, phone=phone, employee_id=employee_id,
        )
        messages.success(request, f'用户「{username}」创建成功')
        return redirect('user_list')

    return redirect('user_list')


@login_required
def user_edit(request, user_id):
    """Admin-only: edit user profile."""
    redirect_resp = _require_admin(request)
    if redirect_resp:
        return redirect_resp

    target_user = get_object_or_404(User.objects.select_related('profile'), pk=user_id)

    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', target_user.first_name)
        target_user.save()

        profile = target_user.profile
        group_id = request.POST.get('group', '')
        if group_id:
            profile.group = Group.objects.get(pk=group_id)
        else:
            profile.group = None
        profile.phone = request.POST.get('phone', '')
        profile.employee_id = request.POST.get('employee_id', '')
        profile.save()

        messages.success(request, f'用户「{target_user.username}」已更新')
        return redirect('user_list')

    groups = Group.objects.all().order_by('name')
    return render(request, 'user_edit.html', {
        'section': 'users',
        'target_user': target_user,
        'groups': groups,
    })


@login_required
def user_reset_password(request, user_id):
    """Admin-only: reset a user's password."""
    redirect_resp = _require_admin(request)
    if redirect_resp:
        return redirect_resp

    target_user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        new_password = request.POST.get('password', '').strip()
        if not new_password:
            messages.error(request, '密码不能为空')
            return redirect('user_list')

        target_user.set_password(new_password)
        target_user.save()
        messages.success(request, f'用户「{target_user.username}」的密码已重置')
        return redirect('user_list')

    return render(request, 'user_reset_password.html', {
        'section': 'users',
        'target_user': target_user,
    })


@login_required
def user_toggle_active(request, user_id):
    """Admin-only: disable or re-enable a user."""
    redirect_resp = _require_admin(request)
    if redirect_resp:
        return redirect_resp

    target_user = get_object_or_404(User, pk=user_id)

    if target_user.username == request.user.username:
        messages.error(request, '不能对自己执行此操作')
        return redirect('user_list')

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save()
        action = '启用' if target_user.is_active else '禁用'
        messages.success(request, f'用户「{target_user.username}」已{action}')

    return redirect('user_list')
