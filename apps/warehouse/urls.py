from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/<int:pk>/', views.inventory_detail, name='inventory_detail'),
    path('inventory/<int:pk>/edit/', views.inventory_edit, name='inventory_edit'),
    path('inventory/<int:pk>/split/', views.inventory_split, name='inventory_split'),
    path('inventory/export/', views.inventory_export, name='inventory_export'),
    path('inventory/import/', views.inventory_import, name='inventory_import'),
    path('inventory/import/template/', views.inventory_import_template, name='inventory_import_template'),
    path('inventory/asset-item/<int:item_id>/edit/', views.asset_item_edit, name='asset_item_edit'),
    path('inventory/<int:pk>/import/', views.asset_item_import, name='asset_item_import'),
    path('inventory/<int:pk>/template/', views.asset_item_template, name='asset_item_template'),
    path('inbound/', views.inbound, name='inbound'),
    path('outbound/', views.outbound, name='outbound'),
    path('log/', views.log_list, name='log_list'),
]
