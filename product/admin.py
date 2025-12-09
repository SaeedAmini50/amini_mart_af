from django.contrib import admin
from .models import Category, Product, Order, OrderItem, Cart

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug']
    search_fields = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    list_display_links = ['title']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'mark', 'port', 'size', 'price', 'quantity', 'category']
    list_filter = ['category', 'mark']
    search_fields = ['title', 'name', 'port', 'size', 'mark']
    list_select_related = ['category']  # بهبود عملکرد
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'name', 'mark', 'category')
        }),
        ('مشخصات محصول', {
            'fields': ('port', 'size', 'description', 'price', 'quantity')
        }),
        ('تصاویر', {
            'fields': ('image', 'image1', 'image2', 'image3', 'image4')
        }),
    )
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)