from django.db import models
from django.contrib.auth.models import User, Group


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
