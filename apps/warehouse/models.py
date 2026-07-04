from django.db import models
from django.contrib.auth.models import User, Group


class Inventory(models.Model):
    """备件库存主表"""
    UNIT_CHOICES = [
        ('个', '个'), ('台', '台'), ('条', '条'), ('块', '块'),
        ('套', '套'), ('根', '根'), ('颗', '颗'), ('包', '包'),
        ('桶', '桶'), ('箱', '箱'),
    ]
    STATUS_CHOICES = [
        ('in_use', '使用中'), ('idle', '闲置'), ('scrapped', '已报废'),
    ]
    QUALITY_CHOICES = [
        ('new', '全新'), ('good', '良好'), ('used', '旧件'), ('repair', '待修'),
    ]
    IMPORTANCE_CHOICES = [
        ('critical', '核心'), ('important', '重要'), ('normal', '一般'),
    ]
    SECURITY_CHOICES = [
        ('secret', '涉密'), ('internal', '内部'), ('public', '非密'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='备件编码')
    name = models.CharField(max_length=200, verbose_name='名称')
    spec = models.CharField(max_length=300, blank=True, verbose_name='规格型号')
    quantity = models.IntegerField(default=0, verbose_name='当前数量')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='个', verbose_name='单位')
    safety_stock = models.IntegerField(default=10, verbose_name='安全库存')
    location = models.CharField(max_length=100, blank=True, verbose_name='存放位置')
    group = models.ForeignKey(
        Group, on_delete=models.PROTECT, related_name='inventories', verbose_name='所属组'
    )
    # 扩展字段（来自需求文档）
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='idle', verbose_name='使用状态')
    quality = models.CharField(max_length=20, choices=QUALITY_CHOICES, default='good', verbose_name='质量等级')
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name='生产厂家')
    configuration = models.TextField(blank=True, verbose_name='配置')
    importance = models.CharField(max_length=20, choices=IMPORTANCE_CHOICES, default='normal', verbose_name='重要程度')
    security_level = models.CharField(max_length=20, choices=SECURITY_CHOICES, default='internal', verbose_name='涉密等级')
    variety_code = models.CharField(max_length=100, blank=True, verbose_name='品种标识码')
    asset_code = models.CharField(max_length=100, blank=True, verbose_name='唯一资产码')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='最后更新')

    class Meta:
        verbose_name = '备件库存'
        verbose_name_plural = '备件库存'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['group']),
        ]

    def __str__(self):
        return f'[{self.code}] {self.name}'

    @property
    def stock_status(self):
        if self.quantity <= 0:
            return 'out'
        if self.quantity < self.safety_stock:
            return 'warn'
        return 'normal'

    @property
    def is_split(self):
        """Whether this inventory has been split into individual asset items."""
        return self.items.exists()


class AssetItem(models.Model):
    """单品明细 — 每个物理个体一条记录"""
    STATUS_CHOICES = [
        ('in_stock', '在库'),
        ('out', '已出库'),
    ]

    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE, related_name='items', verbose_name='所属备件'
    )
    asset_code = models.CharField(max_length=100, blank=True, verbose_name='唯一资产码')
    variety_code = models.CharField(max_length=100, blank=True, verbose_name='品种标识码')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='in_stock', verbose_name='状态'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '单品明细'
        verbose_name_plural = '单品明细'
        ordering = ['inventory', 'id']

    def __str__(self):
        code = self.asset_code or f'#{self.id}'
        return f'{self.inventory.name} - {code}'


class InboundRecord(models.Model):
    """入库记录"""
    TYPE_CHOICES = [
        ('purchase', '采购入库'),
        ('return', '归还入库'),
        ('surplus', '盘盈'),
    ]

    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='inbounds', verbose_name='备件')
    quantity = models.PositiveIntegerField(verbose_name='入库数量')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='purchase', verbose_name='入库类型')
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name='所属组')
    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='操作人')
    note = models.TextField(blank=True, verbose_name='备注/单号')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='入库时间')

    class Meta:
        verbose_name = '入库记录'
        verbose_name_plural = '入库记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'入库: {self.inventory.name} +{self.quantity}'


class OutboundRecord(models.Model):
    """出库记录"""
    PURPOSE_CHOICES = [
        ('repair', '设备维修'),
        ('replace', '设备更换'),
        ('project', '新项目部署'),
        ('borrow', '借用'),
        ('other', '其他'),
    ]

    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='outbounds', verbose_name='备件')
    asset_items = models.ManyToManyField(AssetItem, blank=True, related_name='outbound_records', verbose_name='出库单品')
    quantity = models.PositiveIntegerField(verbose_name='出库数量')
    recipient = models.CharField(max_length=100, verbose_name='领用人')
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='repair', verbose_name='用途')
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name='所属组')
    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='操作人')
    note = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='出库时间')

    class Meta:
        verbose_name = '出库记录'
        verbose_name_plural = '出库记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'出库: {self.inventory.name} -{self.quantity}'


class AuditLog(models.Model):
    """统一出入库流水日志"""
    CHANGE_TYPE_CHOICES = [
        ('inbound', '入库'),
        ('outbound', '出库'),
    ]

    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='logs', verbose_name='备件')
    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='操作人')
    group = models.ForeignKey(Group, on_delete=models.PROTECT, verbose_name='所属组')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES, verbose_name='操作类型')
    delta = models.IntegerField(verbose_name='变动数量')
    before_qty = models.IntegerField(verbose_name='变动前库存')
    after_qty = models.IntegerField(verbose_name='变动后库存')
    note = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        verbose_name = '出入库流水'
        verbose_name_plural = '出入库流水'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['group']),
            models.Index(fields=['change_type']),
        ]

    def __str__(self):
        return f'[{self.get_change_type_display()}] {self.inventory.name} {self.delta:+d}'
