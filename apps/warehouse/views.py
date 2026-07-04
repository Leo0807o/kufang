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
from .export_utils import format_export_datetime


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


def _is_admin_user(request):
    return request.user.is_superuser or getattr(request, 'is_admin', False)


def _default_group_id(request):
    if 'group' in request.GET:
        return request.GET.get('group', '')
    if not _is_admin_user(request) and request.user_group:
        return str(request.user_group.id)
    return ''


def _apply_group_filter(request, queryset):
    if not _is_admin_user(request) and not request.user_group:
        return queryset.none(), ''
    group_id = _default_group_id(request)
    if group_id:
        queryset = queryset.filter(group_id=group_id)
    return queryset, group_id


def _generate_inventory_code(group):
    """Generate a unique inventory code for a group: PREFIX-NNN."""
    from apps.accounts.models import GroupProfile
    prefix = GroupProfile.get_prefix(group)
    last = Inventory.objects.filter(
        code__startswith=prefix, group=group,
    ).order_by('-code').first()
    if last:
        try:
            num = int(last.code.split('-')[1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    code = f'{prefix}-{num:03d}'
    while Inventory.objects.filter(code=code).exists():
        num += 1
        code = f'{prefix}-{num:03d}'
    return code


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
    queryset, group_id = _apply_group_filter(request, queryset)

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
    queryset, group_id = _apply_group_filter(request, queryset)

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
                    format_export_datetime(item.updated_at),
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
                format_export_datetime(item.updated_at),
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
                format_export_datetime(item.updated_at),
            ])

    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'
    return response


# ==================== INVENTORY IMPORT ====================

IMPORT_FIELDS = [
    ('备件编码（留空自动生成）', 'code'),
    ('名称', 'name'),
    ('规格型号', 'spec'),
    ('数量', 'quantity'),
    ('单位', 'unit'),
    ('安全库存', 'safety_stock'),
    ('存放位置', 'location'),
    ('使用状态', 'status'),
    ('质量等级', 'quality'),
    ('生产厂家', 'manufacturer'),
    ('配置', 'configuration'),
    ('重要程度', 'importance'),
    ('涉密等级', 'security_level'),
    ('品种标识码', 'variety_code'),
    ('唯一资产码', 'asset_code'),
]

STATUS_REVERSE = {v: k for k, v in Inventory.STATUS_CHOICES}
QUALITY_REVERSE = {v: k for k, v in Inventory.QUALITY_CHOICES}
IMPORTANCE_REVERSE = {v: k for k, v in Inventory.IMPORTANCE_CHOICES}
SECURITY_REVERSE = {v: k for k, v in Inventory.SECURITY_CHOICES}
UNIT_REVERSE = {v: k for k, v in Inventory.UNIT_CHOICES}


@login_required
def inventory_import_template(request):
    """Download a blank CSV template for inventory import."""
    output = io.StringIO()
    output.write('﻿')  # UTF-8 BOM
    writer = csv.writer(output)

    # Row 1: Field names
    writer.writerow([f[0] for f in IMPORT_FIELDS])

    # Row 2: Example — non-split item
    writer.writerow([
        '', '示例备件A', '型号-X1', '10', '个', '5', 'A区-3架',
        '闲置', '全新', 'XX厂商', '', '一般', '内部',
        'VAR-001', 'ASSET-001',
    ])

    # Row 3: Example — split item (each row = one AssetItem)
    writer.writerow([
        '', '示例备件B', '型号-Y1', '', '个', '3', 'B区-1架',
        '使用中', '良好', 'YY厂商', '', '核心', '涉密',
        'VAR-002', 'ASSET-002',
    ])
    writer.writerow([
        '', '示例备件B', '型号-Y1', '', '个', '', '', '', '', '', '', '', '',
        'VAR-003', 'ASSET-003',
    ])

    # Row 5: Instructions
    writer.writerow([])
    writer.writerow(['说明：'])
    writer.writerow(['1. 备件编码留空则自动生成（格式：组前缀-编号）'])
    writer.writerow(['2. 同一名称+规格型号的多行 = 拆分模式，每行生成一个带独立资产码的单品'])
    writer.writerow(['3. 名称+规格型号唯一的单行 = 整件模式，数量列填总数'])
    writer.writerow(['4. 使用状态: 使用中/闲置/已报废 | 质量等级: 全新/良好/旧件/待修'])
    writer.writerow(['5. 重要程度: 核心/重要/一般 | 涉密等级: 涉密/内部/非密'])

    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="inventory_import_template.csv"'
    return response


@login_required
def inventory_import(request):
    """Bulk import inventory from CSV. Supports both split and non-split modes."""
    user_group = request.user_group
    if not user_group:
        messages.error(request, '您尚未分配业务组，无法导入')
        return redirect('inventory_list')

    if request.method == 'POST':
        csv_file = request.FILES.get('file')
        if not csv_file:
            messages.error(request, '请选择CSV文件')
            return redirect('inventory_list')

        # Parse CSV
        try:
            raw = csv_file.read()
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
            return redirect('inventory_list')

        if len(rows) < 2:
            messages.error(request, 'CSV文件为空或无数据行')
            return redirect('inventory_list')

        # Map field keys to column indices from header
        header = [h.strip().replace('（留空自动生成）', '') for h in rows[0]]
        col_map = {}
        for i, h in enumerate(header):
            for label, key in IMPORT_FIELDS:
                if label.startswith(h) or h.startswith(label[:4]):
                    col_map[key] = i
                    break

        required_cols = {'name'}
        if not required_cols.issubset(col_map.keys()):
            messages.error(request, 'CSV缺少必填列：名称')
            return redirect('inventory_list')

        # Parse data rows (skip empty rows and instruction rows)
        data_rows = []
        for row in rows[1:]:
            if not row or not any(cell.strip() for cell in row):
                continue
            if row[0].strip().startswith('说明'):
                continue
            data_rows.append(row)

        if not data_rows:
            messages.error(request, 'CSV文件中没有数据行')
            return redirect('inventory_list')

        # Group rows by (name, spec) to detect split vs non-split
        def _get(row, key, default=''):
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return default
            return row[idx].strip()

        groups = {}  # (name, spec) -> list of rows
        for row in data_rows:
            name = _get(row, 'name')
            spec = _get(row, 'spec')
            if not name:
                continue
            key = (name, spec)
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        created_inv = 0
        created_ai = 0
        errors = []

        with transaction.atomic():
            for (name, spec), group_rows in groups.items():
                first_row = group_rows[0]
                is_split = len(group_rows) > 1

                # Determine code
                code = _get(first_row, 'code')
                if not code:
                    code = _generate_inventory_code(user_group)
                elif Inventory.objects.filter(code=code).exists():
                    errors.append(f'备件编码「{code}」已存在，跳过「{name}」')
                    continue

                # Parse common fields from first row
                unit_raw = _get(first_row, 'unit')
                unit = UNIT_REVERSE.get(unit_raw, '个')

                qty_str = _get(first_row, 'quantity')
                if is_split:
                    qty = len(group_rows)
                else:
                    qty = int(qty_str) if qty_str else 0

                safety_str = _get(first_row, 'safety_stock')
                safety_stock = int(safety_str) if safety_str else 10

                location = _get(first_row, 'location')
                status_raw = _get(first_row, 'status')
                status = STATUS_REVERSE.get(status_raw, 'idle')
                quality_raw = _get(first_row, 'quality')
                quality = QUALITY_REVERSE.get(quality_raw, 'good')
                manufacturer = _get(first_row, 'manufacturer')
                configuration = _get(first_row, 'configuration')
                importance_raw = _get(first_row, 'importance')
                importance = IMPORTANCE_REVERSE.get(importance_raw, 'normal')
                sec_raw = _get(first_row, 'security_level')
                security_level = SECURITY_REVERSE.get(sec_raw, 'internal')

                # Create Inventory
                inv = Inventory.objects.create(
                    code=code, name=name, spec=spec, quantity=qty, unit=unit,
                    safety_stock=safety_stock, location=location, group=user_group,
                    status=status, quality=quality, manufacturer=manufacturer,
                    configuration=configuration, importance=importance,
                    security_level=security_level,
                    variety_code='',
                    asset_code='',
                )
                created_inv += 1

                if is_split:
                    # Each row = one AssetItem
                    for row in group_rows:
                        variety_code = _get(row, 'variety_code')
                        asset_code = _get(row, 'asset_code')
                        AssetItem.objects.create(
                            inventory=inv,
                            asset_code=asset_code,
                            variety_code=variety_code,
                            status='in_stock',
                        )
                        created_ai += 1
                else:
                    # Single row, codes go on Inventory
                    inv.variety_code = _get(first_row, 'variety_code')
                    inv.asset_code = _get(first_row, 'asset_code')
                    inv.save(update_fields=['variety_code', 'asset_code'])

        if errors:
            for e in errors:
                messages.warning(request, e)

        msg = f'导入完成！创建了 {created_inv} 个备件'
        if created_ai:
            msg += f'、{created_ai} 条单品行'
        messages.success(request, msg)
        return redirect('inventory_list')

    return redirect('inventory_list')


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

                code = _generate_inventory_code(user_group)

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

            outbound_record = OutboundRecord.objects.create(
                inventory=item, quantity=qty, recipient=recipient or request.user.username,
                purpose=purpose, group=user_group, operator=request.user, note=note,
            )
            if in_stock_items:
                outbound_record.asset_items.set(in_stock_items)

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
    queryset, group_id = _apply_group_filter(request, queryset)

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
