from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
# Create your models here.
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=11,blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    date_of_birth = models.CharField(blank=True, null=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
class CustomerDesign(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE) 
    design_description = models.CharField(max_length=500) 
    width = models.FloatField()
    height = models.FloatField()
    thickness = models.FloatField()
    decoration_type = models.CharField(max_length=100, blank=True, null=True) 
    material = models.CharField(max_length=100, blank=True, null=True) 
    model_url = models.TextField(null=True, blank=True) 
    model_image = models.TextField(null=True, blank=True) 
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True) 
    status = models.CharField(max_length=20, choices=[ 
        ('pending', 'Pending'), 
        ('generating', 'Generating Model'), 
        ('generated', 'Model Generated'), 
        ('approved', 'Approved'), 
        ('in_progress', 'In Progress'), 
        ('completed', 'Completed'), 
        ('rejected', 'Rejected') 
    ], default='pending') 
    is_added_to_cart = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self): 
        return f'{self.user} - Custom Design'
    

    
class Category(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    purchase_count = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    default_material = models.CharField(max_length=50, default='oak')  

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_best_seller(self):
        top_product = Product.objects.order_by('-purchase_count').first()
        return top_product and self.id == top_product.id

class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], default='pending')
    address = models.CharField(max_length=500)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='php')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        
    def __str__(self):
        return f'Order {self.id} - {self.status}'
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    customer_design = models.ForeignKey(CustomerDesign, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        if self.product:
            return f'{self.product.name} (x{self.quantity})'
        return f'Custom Design - {self.customer_design.design_description} (x{self.quantity})'

    def clean(self):
        if not self.product and not self.customer_design:
            raise ValidationError('Either product or customer_design must be set')
        if self.product and self.customer_design:
            raise ValidationError('Cannot set both product and customer_design')
        
class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Cart - {self.user.email}'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    customer_design = models.ForeignKey(
        CustomerDesign,
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        limit_choices_to={'status': 'approved'} 
    )
    quantity = models.PositiveIntegerField(default=1) 

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (models.Q(product__isnull=False) & models.Q(customer_design__isnull=True)) |
                    (models.Q(product__isnull=True) & models.Q(customer_design__isnull=False))
                ),
                name='cartitem_must_be_product_or_customer_design',
                violation_error_message='CartItem must be linked to either a Product or a Customer Design, but not both.'
            )
        ]

    def clean(self):
        """
        Custom validation for CartItem.
        """
        super().clean()
        if self.product and self.customer_design:
            raise ValidationError('CartItem cannot be linked to both a Product and a Customer Design.')
        if not self.product and not self.customer_design:
            raise ValidationError('CartItem must be linked to either a Product or a Customer Design.')
        
        if self.customer_design:
            if self.customer_design.status != 'approved':
                raise ValidationError('Only Customer Designs with "approved" status can be added to the cart.')
            if self.customer_design.final_price is None:
                raise ValidationError('Approved Customer Designs must have a final_price to be added to the cart.')

    def __str__(self):
        if self.product:
            return f'Product: {self.product.name} (x{self.quantity}) in {self.cart}'
        elif self.customer_design:
            return f'Design: {self.customer_design.design_description[:30]}... (x{self.quantity}) in {self.cart}'
        return f'Invalid CartItem in {self.cart}' 
    @property
    def item_name(self):
        """Returns the name of the cart item."""
        if self.product:
            return self.product.name 
        elif self.customer_design:
            return self.customer_design.name_for_cart
        return "N/A"

    @property
    def unit_price(self):
        """Returns the unit price of the cart item."""
        if self.product:
            return self.product.price 
        elif self.customer_design:
            return self.customer_design.price_for_cart
        return None

    @property
    def total_price(self):
        """Calculates the total price for this cart item (unit_price * quantity)."""
        price = self.unit_price
        if price is not None and self.quantity > 0:
            return self.quantity * price
        return None

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50, choices=[
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer')
    ])
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Payment for Order {self.order.id}'

class ShippingAddress(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f'Review by {self.user.email} for {self.product.name}'   
        
class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.user.email} for {self.product.name}'