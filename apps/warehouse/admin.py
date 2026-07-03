from django.contrib import admin
from .models import Inventory, InboundRecord, OutboundRecord, AuditLog


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'spec', 'quantity', 'unit', 'group', 'stock_status', 'updated_at']
    list_filter = ['group', 'unit']
    search_fields = ['code', 'name', 'spec']


@admin.register(InboundRecord)
class InboundRecordAdmin(admin.ModelAdmin):
    list_display = ['inventory', 'quantity', 'type', 'group', 'operator', 'created_at']
    list_filter = ['type', 'group']


@admin.register(OutboundRecord)
class OutboundRecordAdmin(admin.ModelAdmin):
    list_display = ['inventory', 'quantity', 'recipient', 'purpose', 'group', 'operator', 'created_at']
    list_filter = ['purpose', 'group']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'change_type', 'inventory', 'delta', 'before_qty', 'after_qty', 'operator', 'group']
    list_filter = ['change_type', 'group', 'created_at']
    search_fields = ['inventory__name', 'operator__username']
