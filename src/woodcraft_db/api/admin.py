from django.contrib import admin
from .models import *

# Register your models here.
 
admin.site.register(CustomUser)
admin.site.register(CustomerDesign)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Payment)
admin.site.register(ShippingAddress)
admin.site.register(Review)