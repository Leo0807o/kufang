import csv
import io
import re
import zipfile

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from .models import UserProfile, GroupProfile


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


# ==================== GROUP MANAGEMENT ====================

PREFIX_PATTERN = re.compile(r'^[A-Z]{2,6}$')
PROTECTED_GROUP = '管理员'


def _require_group_admin(request):
    """Return None if user is admin, else redirect to dashboard with error."""
    if not getattr(request, 'is_admin', False):
        messages.error(request, '您没有管理员权限')
        return redirect('dashboard')
    return None


def _export_group_data_csv(group):
    """Generate a ZIP file of all CSVs for a group's data. Returns bytes."""
    from apps.warehouse.models import Inventory, InboundRecord, OutboundRecord, AuditLog

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:

        # Users
        users = User.objects.filter(profile__group=group).select_related('profile')
        user_csv = io.StringIO()
        user_csv.write('﻿')
        w = csv.writer(user_csv)
        w.writerow(['用户名', '姓名', '电话', '工号'])
        for u in users:
            w.writerow([u.username, u.first_name, u.profile.phone, u.profile.employee_id])
        zf.writestr('用户.csv', user_csv.getvalue().encode('utf-8-sig'))

        # Inventory
        items = Inventory.objects.filter(group=group)
        inv_csv = io.StringIO()
        inv_csv.write('﻿')
        w = csv.writer(inv_csv)
        w.writerow(['备件编码', '名称', '规格型号', '数量', '单位', '安全库存', '存放位置',
                     '使用状态', '质量等级', '生产厂家', '重要程度', '涉密等级', '品种标识码', '唯一资产码'])
        for item in items:
            w.writerow([item.code, item.name, item.spec, item.quantity, item.unit,
                        item.safety_stock, item.location, item.get_status_display(),
                        item.get_quality_display(), item.manufacturer,
                        item.get_importance_display(), item.get_security_level_display(),
                        item.variety_code, item.asset_code])
        zf.writestr('库存.csv', inv_csv.getvalue().encode('utf-8-sig'))

        # Inbound records
        inbounds = InboundRecord.objects.filter(group=group).select_related('inventory', 'operator')
        in_csv = io.StringIO()
        in_csv.write('﻿')
        w = csv.writer(in_csv)
        w.writerow(['备件', '数量', '入库类型', '操作人', '备注', '时间'])
        for r in inbounds:
            w.writerow([r.inventory.name, r.quantity, r.get_type_display(),
                        r.operator.username, r.note, r.created_at.strftime('%Y-%m-%d %H:%M')])
        zf.writestr('入库记录.csv', in_csv.getvalue().encode('utf-8-sig'))

        # Outbound records
        outbounds = OutboundRecord.objects.filter(group=group).select_related('inventory', 'operator')
        out_csv = io.StringIO()
        out_csv.write('﻿')
        w = csv.writer(out_csv)
        w.writerow(['备件', '数量', '领用人', '用途', '操作人', '备注', '时间'])
        for r in outbounds:
            w.writerow([r.inventory.name, r.quantity, r.recipient, r.get_purpose_display(),
                        r.operator.username, r.note, r.created_at.strftime('%Y-%m-%d %H:%M')])
        zf.writestr('出库记录.csv', out_csv.getvalue().encode('utf-8-sig'))

        # Audit logs
        logs = AuditLog.objects.filter(group=group).select_related('inventory', 'operator')
        log_csv = io.StringIO()
        log_csv.write('﻿')
        w = csv.writer(log_csv)
        w.writerow(['时间', '类型', '备件', '变动数量', '变动前', '变动后', '操作人', '备注'])
        for r in logs:
            w.writerow([r.created_at.strftime('%Y-%m-%d %H:%M'), r.get_change_type_display(),
                        r.inventory.name, r.delta, r.before_qty, r.after_qty,
                        r.operator.username, r.note])
        zf.writestr('流水日志.csv', log_csv.getvalue().encode('utf-8-sig'))

    return buf.getvalue()


@login_required
def group_list(request):
    """Admin-only: list all groups."""
    redirect_resp = _require_group_admin(request)
    if redirect_resp:
        return redirect_resp

    groups = Group.objects.prefetch_related('members').order_by('name')

    group_data = []
    for g in groups:
        user_count = g.members.count()
        inventory_count = g.inventories.count()
        profile = getattr(g, 'profile', None)
        group_data.append({
            'group': g,
            'prefix': profile.prefix if profile else '-',
            'user_count': user_count,
            'inventory_count': inventory_count,
            'is_admin_group': g.name == PROTECTED_GROUP,
        })

    return render(request, 'group_list.html', {
        'section': 'groups',
        'group_data': group_data,
    })


@login_required
def group_create(request):
    """Admin-only: create a new group."""
    redirect_resp = _require_group_admin(request)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        prefix = request.POST.get('prefix', '').strip().upper()

        if not name:
            messages.error(request, '组名称不能为空')
            return redirect('group_list')
        if not prefix:
            messages.error(request, '编码前缀不能为空')
            return redirect('group_list')
        if not PREFIX_PATTERN.match(prefix):
            messages.error(request, '编码前缀必须为2-6位大写英文字母')
            return redirect('group_list')
        if Group.objects.filter(name=name).exists():
            messages.error(request, f'组名称「{name}」已存在')
            return redirect('group_list')
        if GroupProfile.objects.filter(prefix=prefix).exists():
            messages.error(request, f'编码前缀「{prefix}」已被占用')
            return redirect('group_list')

        group = Group.objects.create(name=name)
        GroupProfile.objects.create(group=group, prefix=prefix)
        messages.success(request, f'业务组「{name}」（{prefix}）创建成功')
        return redirect('group_list')

    return redirect('group_list')


@login_required
def group_detail(request, group_id):
    """Admin-only: group info card."""
    redirect_resp = _require_group_admin(request)
    if redirect_resp:
        return redirect_resp

    from django.db import models as dj_models
    group = get_object_or_404(Group.objects.prefetch_related('profile'), pk=group_id)
    profile = getattr(group, 'profile', None)
    prefix = profile.prefix if profile else '-'
    is_admin_group = group.name == PROTECTED_GROUP

    from apps.warehouse.models import Inventory, AuditLog
    users = User.objects.filter(profile__group=group).select_related('profile').order_by('username')
    inv_count = Inventory.objects.filter(group=group).count()
    total_qty = Inventory.objects.filter(group=group).aggregate(
        total=dj_models.Sum('quantity'))['total'] or 0
    recent_logs = AuditLog.objects.filter(group=group).select_related(
        'inventory', 'operator')[:10]

    return render(request, 'group_detail.html', {
        'section': 'groups',
        'group': group,
        'prefix': prefix,
        'is_admin_group': is_admin_group,
        'users': users,
        'inv_count': inv_count,
        'total_qty': total_qty,
        'recent_logs': recent_logs,
    })


@login_required
def group_edit(request, group_id):
    """Admin-only: edit group name only. Admin group is protected."""
    redirect_resp = _require_group_admin(request)
    if redirect_resp:
        return redirect_resp

    group = get_object_or_404(Group.objects.prefetch_related('profile'), pk=group_id)

    if group.name == PROTECTED_GROUP:
        messages.error(request, '「管理员」组不可编辑')
        return redirect('group_list')

    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        if not new_name:
            messages.error(request, '组名称不能为空')
            return redirect('group_list')
        if new_name != group.name and Group.objects.filter(name=new_name).exists():
            messages.error(request, f'组名称「{new_name}」已存在')
            return redirect('group_list')
        group.name = new_name
        group.save()
        messages.success(request, f'业务组已更名为「{new_name}」')
        return redirect('group_list')

    profile = getattr(group, 'profile', None)
    prefix = profile.prefix if profile else '-'
    return render(request, 'group_edit.html', {
        'section': 'groups',
        'group': group,
        'prefix': prefix,
        'is_admin_group': True if group.name == PROTECTED_GROUP else False,
    })


@login_required
def group_delete(request, group_id):
    """Admin-only: delete group with ZIP backup. Admin group is protected."""
    redirect_resp = _require_group_admin(request)
    if redirect_resp:
        return redirect_resp

    group = get_object_or_404(Group.objects.prefetch_related('profile'), pk=group_id)

    if group.name == PROTECTED_GROUP:
        messages.error(request, '「管理员」组不可删除')
        return redirect('group_list')

    from apps.warehouse.models import Inventory, InboundRecord, OutboundRecord, AuditLog

    # Gather summary for confirmation page
    user_count = User.objects.filter(profile__group=group).count()
    inv_count = Inventory.objects.filter(group=group).count()
    in_count = InboundRecord.objects.filter(group=group).count()
    out_count = OutboundRecord.objects.filter(group=group).count()
    log_count = AuditLog.objects.filter(group=group).count()
    has_data = any([user_count, inv_count, in_count, out_count, log_count])

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'download':
            zip_data = _export_group_data_csv(group)
            safe_name = group.name.replace('/', '_')
            response = HttpResponse(zip_data, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{safe_name}_backup.zip"'
            return response

        elif action == 'delete':
            if request.POST.get('confirmed') != 'yes':
                messages.error(request, '请勾选确认后再删除')
                return redirect('group_delete', group_id=group.id)

            with transaction.atomic():
                # Detach users
                UserProfile.objects.filter(group=group).update(group=None)
                # Delete all associated data
                AuditLog.objects.filter(group=group).delete()
                OutboundRecord.objects.filter(group=group).delete()
                InboundRecord.objects.filter(group=group).delete()
                Inventory.objects.filter(group=group).delete()
                # Delete GroupProfile and Group
                GroupProfile.objects.filter(group=group).delete()
                group.delete()
            messages.success(request, f'业务组「{group.name}」已删除，用户已设为未分组')
            return redirect('group_list')

    return render(request, 'group_delete.html', {
        'section': 'groups',
        'group': group,
        'is_admin_group': True if group.name == PROTECTED_GROUP else False,
        'user_count': user_count,
        'inv_count': inv_count,
        'in_count': in_count,
        'out_count': out_count,
        'log_count': log_count,
        'has_data': has_data,
    })
