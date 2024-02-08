from django.contrib import admin

from backend.models import MyUser, Product, Order, OrderItem

# Register your models here.


admin.site.register(MyUser)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)