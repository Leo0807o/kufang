# -*- coding: utf-8 -*-
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from apps.accounts.models import UserProfile, GroupProfile
from apps.warehouse.models import Inventory, InboundRecord, OutboundRecord, AuditLog
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Create demo seed data: groups + users + inventory + logs'

    def handle(self, *args, **options):
        # Fix GBK encoding on Windows
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')

        self.stdout.write('[Seed] Creating demo data...')

        # ===== Create Groups =====
        group_prefixes = {
            '主机组': 'HOST',
            '冷却组': 'COOL',
            '电力组': 'ELEC',
            '管理员': '',  # Admin group has no prefix
        }
        groups = {}
        for name in ['主机组', '冷却组', '电力组', '管理员']:
            group, created = Group.objects.get_or_create(name=name)
            groups[name] = group
            action = 'created' if created else 'exists'
            prefix = group_prefixes.get(name, '')
            if prefix:
                gp, gp_created = GroupProfile.objects.get_or_create(
                    group=group, defaults={'prefix': prefix},
                )
                if not gp_created and gp.prefix != prefix:
                    gp.prefix = prefix
                    gp.save()
            self.stdout.write(f'  [{"OK" if created else "SKIP"}] Group: {name} ({action})')

        # ===== Create Users =====
        users_data = [
            ('zhangsan', 'Zhang San', '主机组'),
            ('lisi', 'Li Si', '主机组'),
            ('wangwu', 'Wang Wu', '冷却组'),
            ('zhaoliu', 'Zhao Liu', '冷却组'),
            ('sunqi', 'Sun Qi', '电力组'),
            ('zhouba', 'Zhou Ba', '电力组'),
            ('admin', 'Admin', '管理员'),
        ]

        users = {}
        for username, display_name, group_name in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': display_name, 'is_staff': True},
            )
            if created:
                user.set_password('demo123')
                user.save()
            ugroup = groups.get(group_name) if group_name else None
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'group': ugroup, 'employee_id': f'EMP-{username.upper()}'},
            )
            profile = user.profile
            if profile.group != ugroup:
                profile.group = ugroup
                profile.save()
            users[username] = user
            self.stdout.write(f'  [{"OK" if created else "SKIP"}] User: {username} -> {group_name or "admin"}')

        # Superuser
        admin_user = users.get('admin')
        if admin_user and not admin_user.is_superuser:
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.save()

        # ===== Create Inventory =====
        now = datetime.now()
        inventory_items = [
            # 主机组 (A)
            {'code': 'HOST-001', 'name': 'DDR4 32GB 内存条', 'spec': 'DDR4-3200 ECC', 'qty': 2, 'unit': '条', 'safety': 10, 'location': 'A-01-03', 'group': '主机组'},
            {'code': 'HOST-002', 'name': 'Intel Xeon 4210 CPU', 'spec': 'Silver 4210 2.2GHz', 'qty': 0, 'unit': '颗', 'safety': 5, 'location': 'A-01-05', 'group': '主机组'},
            {'code': 'HOST-003', 'name': 'SAS 2.4T 10K 硬盘', 'spec': '2.4TB 10000RPM SAS', 'qty': 5, 'unit': '块', 'safety': 15, 'location': 'A-02-01', 'group': '主机组'},
            {'code': 'HOST-004', 'name': 'RAID 阵列卡', 'spec': 'LSI MegaRAID 9361-8i', 'qty': 3, 'unit': '块', 'safety': 8, 'location': 'A-02-04', 'group': '主机组'},
            {'code': 'HOST-005', 'name': '光模块 10G SFP+', 'spec': 'SFP+ 10G SR 850nm', 'qty': 8, 'unit': '个', 'safety': 20, 'location': 'A-03-01', 'group': '主机组'},
            {'code': 'HOST-006', 'name': '光纤跳线 LC-LC 3m', 'spec': 'LC-LC OM3 多模', 'qty': 45, 'unit': '根', 'safety': 15, 'location': 'A-03-02', 'group': '主机组'},
            {'code': 'HOST-007', 'name': '服务器电源 2000W', 'spec': '2000W Platinum', 'qty': 12, 'unit': '个', 'safety': 6, 'location': 'A-01-08', 'group': '主机组'},
            {'code': 'HOST-008', 'name': '主板 Supermicro X11', 'spec': 'X11DPi-NT', 'qty': 4, 'unit': '块', 'safety': 3, 'location': 'A-02-06', 'group': '主机组'},
            # 冷却组 (B)
            {'code': 'COOL-001', 'name': '空调滤网', 'spec': '600x600mm G4', 'qty': 30, 'unit': '个', 'safety': 10, 'location': 'B-01-01', 'group': '冷却组'},
            {'code': 'COOL-002', 'name': '冷却液', 'spec': '25L 乙二醇', 'qty': 8, 'unit': '桶', 'safety': 5, 'location': 'B-01-03', 'group': '冷却组'},
            # 电力组 (C)
            {'code': 'ELEC-001', 'name': '电源模块 2000W', 'spec': 'AC-DC 2000W 48V', 'qty': 20, 'unit': '个', 'safety': 10, 'location': 'C-01-01', 'group': '电力组'},
            {'code': 'ELEC-002', 'name': 'UPS 电池', 'spec': '12V 100Ah', 'qty': 15, 'unit': '块', 'safety': 8, 'location': 'C-01-04', 'group': '电力组'},
        ]

        created_items = {}
        for data in inventory_items:
            group = groups[data['group']]
            item, created = Inventory.objects.get_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'spec': data['spec'],
                    'quantity': data['qty'],
                    'unit': data['unit'],
                    'safety_stock': data['safety'],
                    'location': data['location'],
                    'group': group,
                    'status': 'idle',
                    'quality': 'good',
                    'manufacturer': '',
                    'importance': 'normal',
                    'security_level': 'internal',
                },
            )
            if not created:
                item.quantity = data['qty']
                item.save()
            created_items[data['code']] = item
        self.stdout.write(f'  [OK] Inventory: {len(inventory_items)} items')

        # ===== Create Logs =====
        log_entries = [
            {'days_ago': 1, 'hours': 14, 'min': 32, 'op': 'lisi', 'group': '主机组', 'code': 'HOST-001', 'type': 'inbound', 'delta': 12, 'before': 2, 'after': 14, 'note': '采购入库 PO-2026-0782'},
            {'days_ago': 1, 'hours': 13, 'min': 15, 'op': 'wangwu', 'group': '冷却组', 'code': 'COOL-001', 'type': 'outbound', 'delta': -3, 'before': 33, 'after': 30, 'note': '季度更换'},
            {'days_ago': 1, 'hours': 11, 'min': 48, 'op': 'zhangsan', 'group': '主机组', 'code': 'HOST-003', 'type': 'outbound', 'delta': -2, 'before': 7, 'after': 5, 'note': '设备维修 WO-2026-451'},
            {'days_ago': 1, 'hours': 10, 'min': 20, 'op': 'zhouba', 'group': '电力组', 'code': 'ELEC-001', 'type': 'inbound', 'delta': 5, 'before': 15, 'after': 20, 'note': '采购入库 PO-2026-0790'},
            {'days_ago': 2, 'hours': 9, 'min': 5, 'op': 'lisi', 'group': '主机组', 'code': 'HOST-002', 'type': 'outbound', 'delta': -1, 'before': 1, 'after': 0, 'note': '紧急更换'},
            {'days_ago': 3, 'hours': 17, 'min': 30, 'op': 'zhangsan', 'group': '主机组', 'code': 'HOST-006', 'type': 'inbound', 'delta': 3, 'before': 42, 'after': 45, 'note': '盘盈'},
            {'days_ago': 4, 'hours': 15, 'min': 0, 'op': 'lisi', 'group': '主机组', 'code': 'HOST-001', 'type': 'inbound', 'delta': 10, 'before': 4, 'after': 14, 'note': '采购入库 PO-2026-0765'},
            {'days_ago': 5, 'hours': 10, 'min': 30, 'op': 'zhangsan', 'group': '主机组', 'code': 'HOST-004', 'type': 'outbound', 'delta': -2, 'before': 5, 'after': 3, 'note': '新项目部署'},
            {'days_ago': 7, 'hours': 9, 'min': 0, 'op': 'lisi', 'group': '主机组', 'code': 'HOST-005', 'type': 'outbound', 'delta': -4, 'before': 12, 'after': 8, 'note': '网络扩容'},
            {'days_ago': 8, 'hours': 14, 'min': 20, 'op': 'zhouba', 'group': '电力组', 'code': 'ELEC-002', 'type': 'outbound', 'delta': -5, 'before': 20, 'after': 15, 'note': '电池更换计划'},
        ]

        # Clear existing
        AuditLog.objects.all().delete()
        InboundRecord.objects.all().delete()
        OutboundRecord.objects.all().delete()

        for entry in log_entries:
            dt = now - timedelta(days=entry['days_ago'])
            dt = dt.replace(hour=entry['hours'], minute=entry['min'], second=0)
            operator = users[entry['op']]
            group = groups[entry['group']]
            item = created_items[entry['code']]

            AuditLog.objects.create(
                inventory=item, operator=operator, group=group,
                change_type=entry['type'],
                delta=entry['delta'],
                before_qty=entry['before'],
                after_qty=entry['after'],
                note=entry['note'],
                created_at=dt,
            )

            if entry['type'] == 'inbound':
                InboundRecord.objects.create(
                    inventory=item, quantity=abs(entry['delta']),
                    type='purchase' if '采购' in entry['note'] else ('surplus' if '盘盈' in entry['note'] else 'return'),
                    group=group, operator=operator, note=entry['note'],
                    created_at=dt,
                )
            else:
                OutboundRecord.objects.create(
                    inventory=item, quantity=abs(entry['delta']),
                    recipient=operator.first_name or operator.username,
                    purpose='repair' if '维修' in entry['note'] else ('project' if '项目' in entry['note'] else 'other'),
                    group=group, operator=operator, note=entry['note'],
                    created_at=dt,
                )

        self.stdout.write(f'  [OK] Logs: {len(log_entries)} entries')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('[DONE] Seed data created!'))
        self.stdout.write('')
        self.stdout.write('Login info (password: demo123):')
        self.stdout.write('  zhangsan -> 主机组 (A)')
        self.stdout.write('  lisi     -> 主机组 (A)')
        self.stdout.write('  wangwu   -> 冷却组 (B)')
        self.stdout.write('  zhaoliu  -> 冷却组 (B)')
        self.stdout.write('  sunqi    -> 电力组 (C)')
        self.stdout.write('  zhouba   -> 电力组 (C)')
        self.stdout.write('  admin    -> superuser')
