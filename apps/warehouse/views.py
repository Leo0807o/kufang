import csv
import io
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.db import models, transaction
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator, EmptyPage

from .models import Inventory, AssetItem, InboundRecord, OutboundRecord, AuditLog
from .decorators import require_group_owner


PAGE_SIZE = 20


def _get_group_display(group):
    """Helper to map group name to a deterministic CSS tag class (a-g)."""
    name = group.name if hasattr(group, 'name') else str(group)
    # Use group id modulo 7 for deterministic color assignment
    if hasattr(group, 'id'):
        idx = group.id % 7
    else:
        idx = hash(name) % 7
    return chr(ord('a') + idx)


def _group_choices():
    """Return all groups for filter dropdowns."""
    from django.contrib.auth.models import Group
    return Group.objects.all()


def _paginate(request, queryset, page_size=PAGE_SIZE):
    """Helper: paginate a queryset and return page_obj + range."""
    p = Paginator(queryset, page_size)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = p.page(page_num)
    except EmptyPage:
        page_obj = p.page(1)
    return page_obj


# ==================== DASHBOARD ====================

@login_required
def dashboard(request):
    user_group = request.user_group
    ctx = {'section': 'dashboard'}

    if user_group:
        # 本组库存总数
        total_qty = Inventory.objects.filter(group=user_group).aggregate(
            total=Sum('quantity'))['total'] or 0
        total_types = Inventory.objects.filter(group=user_group).count()

        # 本月入库次数
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_in = InboundRecord.objects.filter(
            group=user_group, created_at__gte=month_start).count()
        month_out = OutboundRecord.objects.filter(
            group=user_group, created_at__gte=month_start).count()

        # 低库存预警
        low_stock = Inventory.objects.filter(
            group=user_group, quantity__lt=models.F('safety_stock')
        ).order_by('quantity')[:5]

        ctx.update({
            'total_qty': total_qty,
            'total_types': total_types,
            'month_in': month_in,
            'month_out': month_out,
            'low_stock': low_stock,
            'low_stock_count': Inventory.objects.filter(
                group=user_group, quantity__lt=models.F('safety_stock')
            ).count(),
        })
    else:
        ctx.update({
            'total_qty': 0, 'total_types': 0,
            'month_in': 0, 'month_out': 0,
            'low_stock': [], 'low_stock_count': 0,
        })

    # 全局动态（最近 10 条）
    recent_logs = AuditLog.objects.select_related('inventory', 'operator', 'group').all()[:10]
    ctx['recent_logs'] = recent_logs

    return render(request, 'dashboard.html', ctx)


# ==================== INVENTORY LIST ====================

@login_required
def inventory_list(request):
    queryset = Inventory.objects.select_related('group').all()

    # Search
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(spec__icontains=search)
        )

    # Filter by group
    group_id = request.GET.get('group', '')
    if group_id:
        queryset = queryset.filter(group_id=group_id)

    # Filter by status
    status = request.GET.get('status', '')
    if status == 'out':
        queryset = queryset.filter(quantity__lte=0)
    elif status == 'warn':
        queryset = queryset.filter(quantity__gt=0, quantity__lt=models.F('safety_stock'))
    elif status == 'normal':
        queryset = queryset.filter(quantity__gte=models.F('safety_stock'))

    # Paginate (must be ordered)
    page_obj = _paginate(request, queryset.order_by('-updated_at'))
    user_group = request.user_group

    ctx = {
        'section': 'inventory',
        'page_obj': page_obj,
        'user_group': user_group,
        'groups': _group_choices(),
        'search': search,
        'selected_group': group_id,
        'selected_status': status,
    }
    return render(request, 'inventory_list.html', ctx)


# ==================== INVENTORY DETAIL ====================

@login_required
def inventory_detail(request, pk):
    item = get_object_or_404(Inventory.objects.select_related('group'), pk=pk)
    is_owner = (request.user_group is not None and item.group == request.user_group)
    asset_items = item.items.all()
    ctx = {
        'section': 'inventory',
        'item': item,
        'is_owner': is_owner,
        'group_class': _get_group_display(item.group),
        'asset_items': asset_items,
    }
    return render(request, 'inventory_detail.html', ctx)


# ==================== INVENTORY SPLIT ====================

@login_required
def inventory_split(request, pk):
    """Split an inventory into individual AssetItem records."""
    item = get_object_or_404(Inventory, pk=pk)

    # Only same-group members can split
    if not request.user_group or item.group != request.user_group:
        return HttpResponseForbidden('您无权操作其他组的备件')

    if item.is_split:
        messages.warning(request, f'「{item.name}」已经拆分过了')
        return redirect('inventory_detail', pk=item.pk)

    if request.method == 'POST':
        qty = item.quantity
        if qty <= 0:
            messages.error(request, '库存为0，无法拆分')
            return redirect('inventory_detail', pk=item.pk)

        with transaction.atomic():
            for i in range(qty):
                AssetItem.objects.create(
                    inventory=item,
                    asset_code='',
                    variety_code='',
                    status='in_stock',
                )
        messages.success(request, f'「{item.name}」已拆分为 {qty} 条单品行，可逐一补充资产码')
        return redirect('inventory_detail', pk=item.pk)

    return render(request, 'inventory_split_confirm.html', {
        'section': 'inventory',
        'item': item,
    })


# ==================== ASSET ITEM EDIT ====================

@login_required
def asset_item_edit(request, item_id):
    """Edit a single asset item's codes."""
    asset_item = get_object_or_404(AssetItem.objects.select_related('inventory'), pk=item_id)
    inv = asset_item.inventory

    if not request.user_group or inv.group != request.user_group:
        return HttpResponseForbidden('您无权操作其他组的备件')

    if request.method == 'POST':
        asset_item.asset_code = request.POST.get('asset_code', '').strip()
        asset_item.variety_code = request.POST.get('variety_code', '').strip()
        asset_item.save()
        messages.success(request, '单品信息已更新')
        return redirect('inventory_detail', pk=inv.pk)

    return render(request, 'asset_item_edit.html', {
        'section': 'inventory',
        'asset_item': asset_item,
        'item': inv,
    })


# ==================== ASSET ITEM TEMPLATE CSV ====================

@login_required
def asset_item_template(request, pk):
    """Download the CSV template for asset code import, pre-filled with item code."""
    item = get_object_or_404(Inventory, pk=pk)
    output = io.StringIO()
    output.write('﻿')  # UTF-8 BOM
    writer = csv.writer(output)
    writer.writerow(['全局唯一编码', '唯一资产码', '品种标识码'])
    in_stock_items = item.items.filter(status='in_stock')
    for idx, ai in enumerate(in_stock_items, 1):
        writer.writerow([f'{item.code}-{idx}', '', ''])
    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="asset_code_template.csv"'
    return response


# ==================== ASSET ITEM IMPORT ====================

@login_required
def asset_item_import(request, pk):
    """Bulk import asset codes from CSV for a split inventory."""
    item = get_object_or_404(Inventory, pk=pk)

    if not request.user_group or item.group != request.user_group:
        return HttpResponseForbidden('您无权操作其他组的备件')

    if not item.is_split:
        messages.error(request, '请先拆分单品后再导入')
        return redirect('inventory_detail', pk=item.pk)

    if request.method == 'POST':
        csv_file = request.FILES.get('file')
        if not csv_file:
            messages.error(request, '请选择CSV文件')
            return redirect('inventory_detail', pk=item.pk)

        try:
            raw = csv_file.read()
            # Try UTF-8 BOM first, then GBK (Excel on Chinese Windows), then plain UTF-8
            content = None
            for enc in ['utf-8-sig', 'gbk', 'utf-8']:
                try:
                    content = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if content is None:
                raise ValueError('无法识别文件编码，请使用 UTF-8 或 GBK 编码')
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
        except Exception as e:
            messages.error(request, f'CSV文件解析失败: {e}')
            return redirect('inventory_detail', pk=item.pk)

        if len(rows) < 2:
            messages.error(request, 'CSV文件为空或无数据行')
            return redirect('inventory_detail', pk=item.pk)

        # Header row: 全局唯一编码, 唯一资产码, 品种标识码
        data_rows = rows[1:]

        # Get in_stock items in order
        items = list(item.items.filter(status='in_stock').order_by('id'))

        updated = 0
        for i, row in enumerate(data_rows):
            if i >= len(items):
                break
            # Support 2 or 3 column format
            if len(row) >= 3:
                items[i].asset_code = (row[1] or '').strip()
                items[i].variety_code = (row[2] or '').strip()
            elif len(row) >= 2:
                items[i].asset_code = (row[0] or '').strip()
                items[i].variety_code = (row[1] or '').strip()
            elif len(row) >= 1:
                items[i].asset_code = (row[0] or '').strip()
            items[i].save(update_fields=['asset_code', 'variety_code'])
            updated += 1

        messages.success(request, f'导入完成！更新了 {updated} 条单品行')
        return redirect('inventory_detail', pk=item.pk)

    return render(request, 'asset_item_import.html', {
        'section': 'inventory',
        'item': item,
    })


# ==================== INVENTORY EDIT ====================

@login_required
@require_group_owner
def inventory_edit(request, pk):
    item = get_object_or_404(Inventory, pk=pk)

    if request.method == 'POST':
        item.name = request.POST.get('name', item.name)
        item.spec = request.POST.get('spec', item.spec)
        item.unit = request.POST.get('unit', item.unit)
        item.safety_stock = int(request.POST.get('safety_stock', item.safety_stock))
        item.location = request.POST.get('location', item.location)
        item.status = request.POST.get('status', item.status)
        item.quality = request.POST.get('quality', item.quality)
        item.manufacturer = request.POST.get('manufacturer', item.manufacturer)
        item.configuration = request.POST.get('configuration', item.configuration)
        item.importance = request.POST.get('importance', item.importance)
        item.security_level = request.POST.get('security_level', item.security_level)
        item.variety_code = request.POST.get('variety_code', item.variety_code)
        item.asset_code = request.POST.get('asset_code', item.asset_code)
        item.save()
        messages.success(request, f'备件「{item.name}」已更新')
        return redirect('inventory_list')

    ctx = {
        'section': 'inventory',
        'item': item,
    }
    return render(request, 'inventory_edit.html', ctx)


# ==================== INVENTORY EXPORT ====================

@login_required
def inventory_export(request):
    user_group = request.user_group
    queryset = Inventory.objects.select_related('group').all()

    # Apply same filters as list
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(spec__icontains=search)
        )
    group_id = request.GET.get('group', '')
    if group_id:
        queryset = queryset.filter(group_id=group_id)

    # Create CSV response with BOM for Excel Chinese support
    output = io.StringIO()
    output.write('﻿')  # UTF-8 BOM
    writer = csv.writer(output)
    writer.writerow([
        '备件编码', '名称', '规格型号', '数量', '单位', '所属组',
        '安全库存', '存放位置', '使用状态', '质量等级', '生产厂家',
        '重要程度', '涉密等级', '品种标识码', '唯一资产码', '状态', '最后更新'
    ])
    for item in queryset:
        asset_items = list(item.items.all())
        if asset_items:
            # Export each asset item as a separate row
            for idx, ai in enumerate(asset_items, 1):
                code = f'{item.code}-{idx}'
                writer.writerow([
                    code, item.name, item.spec, 1, item.unit,
                    item.group.name if item.group else '', item.safety_stock,
                    item.location, item.get_status_display(), item.get_quality_display(),
                    item.manufacturer, item.get_importance_display(),
                    item.get_security_level_display(),
                    ai.variety_code or item.variety_code,
                    ai.asset_code or item.asset_code,
                    ai.get_status_display(),
                    item.updated_at.strftime('%Y-%m-%d %H:%M') if item.updated_at else '',
                ])
        elif item.quantity > 0:
            # Not split — single row
            writer.writerow([
                item.code, item.name, item.spec, item.quantity, item.unit,
                item.group.name if item.group else '', item.safety_stock,
                item.location, item.get_status_display(), item.get_quality_display(),
                item.manufacturer, item.get_importance_display(),
                item.get_security_level_display(), item.variety_code, item.asset_code,
                '在库',
                item.updated_at.strftime('%Y-%m-%d %H:%M') if item.updated_at else '',
            ])
        else:
            # Zero quantity — still export one row
            writer.writerow([
                item.code, item.name, item.spec, 0, item.unit,
                item.group.name if item.group else '', item.safety_stock,
                item.location, item.get_status_display(), item.get_quality_display(),
                item.manufacturer, item.get_importance_display(),
                item.get_security_level_display(), item.variety_code, item.asset_code,
                '缺货',
                item.updated_at.strftime('%Y-%m-%d %H:%M') if item.updated_at else '',
            ])

    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'
    return response


# ==================== INBOUND ====================

@login_required
def inbound(request):
    user_group = request.user_group
    if not user_group:
        messages.error(request, '您尚未分配业务组，无法操作')
        return redirect('dashboard')

    # Parts for dropdown (existing in same group + all for reference)
    existing_parts = Inventory.objects.filter(group=user_group).order_by('name')

    if request.method == 'POST':
        part_action = request.POST.get('part_action', 'existing')  # existing or new
        qty_key = 'quantity_new' if part_action == 'new' else 'quantity'
        qty = int(request.POST.get(qty_key, 0) or 0)
        inbound_type = request.POST.get('type', 'purchase')
        note = request.POST.get('note', '')

        if qty <= 0:
            messages.error(request, '入库数量必须为正整数')
            return render(request, 'inbound.html', {
                'section': 'inbound',
                'existing_parts': existing_parts,
                'units': dict(Inventory.UNIT_CHOICES),
                'types': dict(InboundRecord.TYPE_CHOICES),
                'post_data': request.POST,
            })

        with transaction.atomic():
            if part_action == 'existing':
                part_id = request.POST.get('part_id')
                item = get_object_or_404(Inventory, pk=part_id)
                if item.group != user_group:
                    return HttpResponseForbidden('您无权操作其他组的备件')
                item.quantity = models.F('quantity') + qty
                item.save(update_fields=['quantity', 'updated_at'])
                item.refresh_from_db()

                # If already split, auto-create new asset items
                if item.is_split:
                    for _ in range(qty):
                        AssetItem.objects.create(
                            inventory=item,
                            asset_code='',
                            variety_code='',
                            status='in_stock',
                        )
            else:
                # New part — auto-generate code
                name = request.POST.get('name', '').strip()
                if not name:
                    messages.error(request, '新备件名称为必填项')
                    return render(request, 'inbound.html', {
                        'section': 'inbound',
                        'existing_parts': existing_parts,
                        'units': dict(Inventory.UNIT_CHOICES),
                        'types': dict(InboundRecord.TYPE_CHOICES),
                        'post_data': request.POST,
                    })

                # Auto-generate code: group-prefix + number
                from apps.accounts.models import GroupProfile
                prefix = GroupProfile.get_prefix(user_group)
                last = Inventory.objects.filter(
                    code__startswith=prefix,
                    group=user_group,
                ).order_by('-code').first()
                if last:
                    try:
                        num = int(last.code.split('-')[1]) + 1
                    except (IndexError, ValueError):
                        num = 1
                else:
                    num = 1
                code = f'{prefix}-{num:03d}'

                # Ensure unique
                while Inventory.objects.filter(code=code).exists():
                    num += 1
                    code = f'{prefix}-{num:03d}'

                item = Inventory.objects.create(
                    code=code, name=name,
                    spec=request.POST.get('spec', ''),
                    quantity=qty,
                    unit=request.POST.get('unit', '个'),
                    safety_stock=int(request.POST.get('safety_stock', 10) or 10),
                    location=request.POST.get('location', ''),
                    group=user_group,
                    status=request.POST.get('status', 'idle'),
                    quality=request.POST.get('quality', 'good'),
                    manufacturer=request.POST.get('manufacturer', ''),
                    configuration=request.POST.get('configuration', ''),
                    importance=request.POST.get('importance', 'normal'),
                    security_level=request.POST.get('security_level', 'internal'),
                    variety_code=request.POST.get('variety_code', ''),
                    asset_code=request.POST.get('asset_code', ''),
                )

            before_qty = item.quantity - qty if part_action == 'existing' else 0

            # Create inbound record
            InboundRecord.objects.create(
                inventory=item, quantity=qty, type=inbound_type,
                group=user_group, operator=request.user, note=note,
            )

            # Create audit log
            AuditLog.objects.create(
                inventory=item, operator=request.user, group=user_group,
                change_type='inbound', delta=+qty,
                before_qty=before_qty, after_qty=item.quantity,
                note=f'{dict(InboundRecord.TYPE_CHOICES).get(inbound_type, inbound_type)} · {note}',
            )

        messages.success(request, f'入库成功！{item.name} +{qty}，当前库存 {item.quantity}')
        return redirect('inventory_list')

    ctx = {
        'section': 'inbound',
        'existing_parts': existing_parts,
        'units': dict(Inventory.UNIT_CHOICES),
        'types': dict(InboundRecord.TYPE_CHOICES),
        'post_data': {},
    }
    return render(request, 'inbound.html', ctx)


# ==================== OUTBOUND ====================

@login_required
def outbound(request):
    user_group = request.user_group
    if not user_group:
        messages.error(request, '您尚未分配业务组，无法操作')
        return redirect('dashboard')

    # Only show parts with stock from user's own group
    available_parts = Inventory.objects.filter(
        group=user_group, quantity__gt=0
    ).order_by('name')

    if request.method == 'POST':
        part_id = request.POST.get('part_id')
        qty = int(request.POST.get('quantity', 0) or 0)
        recipient = request.POST.get('recipient', '').strip()
        purpose = request.POST.get('purpose', 'repair')
        note = request.POST.get('note', '')

        if not part_id:
            messages.error(request, '请选择备件')
            return render(request, 'outbound.html', {
                'section': 'outbound',
                'available_parts': available_parts,
                'purposes': dict(OutboundRecord.PURPOSE_CHOICES),
                'post_data': request.POST,
            })
        if qty <= 0:
            messages.error(request, '出库数量必须为正整数')
            return render(request, 'outbound.html', {
                'section': 'outbound',
                'available_parts': available_parts,
                'purposes': dict(OutboundRecord.PURPOSE_CHOICES),
                'post_data': request.POST,
            })

        with transaction.atomic():
            item = get_object_or_404(
                Inventory.objects.select_for_update(), pk=part_id
            )
            if item.group != user_group:
                return HttpResponseForbidden('您无权操作其他组的备件')
            if qty > item.quantity:
                messages.error(request, f'出库数量({qty})超过当前库存({item.quantity})')
                return render(request, 'outbound.html', {
                    'section': 'outbound',
                    'available_parts': available_parts,
                    'purposes': dict(OutboundRecord.PURPOSE_CHOICES),
                    'post_data': request.POST,
                })

            before_qty = item.quantity
            item.quantity = models.F('quantity') - qty
            item.save(update_fields=['quantity', 'updated_at'])
            item.refresh_from_db()

            # Deduct from asset items (in_stock first)
            in_stock_items = list(item.items.filter(status='in_stock').order_by('id')[:qty])
            for ai in in_stock_items:
                ai.status = 'out'
                ai.save(update_fields=['status'])

            OutboundRecord.objects.create(
                inventory=item, quantity=qty, recipient=recipient or request.user.username,
                purpose=purpose, group=user_group, operator=request.user, note=note,
            )

            AuditLog.objects.create(
                inventory=item, operator=request.user, group=user_group,
                change_type='outbound', delta=-qty,
                before_qty=before_qty, after_qty=item.quantity,
                note=f'{dict(OutboundRecord.PURPOSE_CHOICES).get(purpose, purpose)} · {note}',
            )

        messages.success(request, f'出库成功！{item.name} -{qty}，剩余库存 {item.quantity}')
        return redirect('inventory_list')

    ctx = {
        'section': 'outbound',
        'available_parts': available_parts,
        'purposes': dict(OutboundRecord.PURPOSE_CHOICES),
        'post_data': {},
    }
    return render(request, 'outbound.html', ctx)


# ==================== LOG LIST ====================

@login_required
def log_list(request):
    queryset = AuditLog.objects.select_related('inventory', 'operator', 'group').all()

    # Search
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(inventory__name__icontains=search) |
            Q(operator__username__icontains=search)
        )

    # Filter by type
    log_type = request.GET.get('type', '')
    if log_type in ('inbound', 'outbound'):
        queryset = queryset.filter(change_type=log_type)

    # Filter by group
    group_id = request.GET.get('group', '')
    if group_id:
        queryset = queryset.filter(group_id=group_id)

    page_obj = _paginate(request, queryset)

    ctx = {
        'section': 'log',
        'page_obj': page_obj,
        'groups': _group_choices(),
        'search': search,
        'selected_type': log_type,
        'selected_group': group_id,
    }
    return render(request, 'log.html', ctx)
