from ninja import ModelSchema, Schema
from .models import CustomUser as User, CustomerDesign, Category, Product, CartItem

class SignInSchema(ModelSchema):
    class Meta:
        model = User
        fields = ['email', 'password']
        
class SignUpSchema(ModelSchema):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password']

class CustomerDesignSchema(Schema):
    design_description: str
    decoration_type: str
    material: str
    height: float
    width: float
    thickness: float

class CategorySchema(ModelSchema):
    class Meta:
        model = Category
        fields = '__all__'
        exclude = ['created_at', 'updated_at']

class ProductSchema(ModelSchema):
    class Meta:
        model = Product
        fields = '__all__'
        exclude = ['created_at', 'updated_at']

class AddToCartSchema(Schema):
    user: int
    product_id: int
    quantity: int
    message: str

class CartItemSchema(Schema):
    cart_items: list
    total_price: float
    total_items: int