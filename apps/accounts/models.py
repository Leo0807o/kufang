from django.db import models
from django.contrib.auth.models import User, Group


class GroupProfile(models.Model):
    """Extend Django Group with a business prefix for auto-generating inventory codes."""
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='profile')
    prefix = models.CharField(
        max_length=6,
        unique=True,
        verbose_name='编码前缀',
        help_text='2-6位大写字母，创建后不可修改。用于生成备件编码，如 HOST-001。',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '业务组扩展'
        verbose_name_plural = '业务组扩展'

    def __str__(self):
        return f'{self.group.name} ({self.prefix})'

    @classmethod
    def get_prefix_map(cls):
        """Return a dict mapping group name -> prefix for all groups."""
        return {gp.group.name: gp.prefix for gp in cls.objects.select_related('group').all()}

    @classmethod
    def get_prefix(cls, group):
        """Get prefix for a specific group, falling back to 'PART'."""
        try:
            return group.profile.prefix
        except GroupProfile.DoesNotExist:
            return 'PART'


class UserProfile(models.Model):
    """Extend Django User with business group binding."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name='所属业务组'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='电话')
    employee_id = models.CharField(max_length=50, blank=True, verbose_name='工号')

    class Meta:
        verbose_name = '用户扩展'
        verbose_name_plural = '用户扩展'

    def __str__(self):
        return f'{self.user.username} - {self.group.name if self.group else "未分组"}'
