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

class CreateCustomerDesignSchema(Schema):
    user_id: int
    material: str
    decoration_type: str
    design_description: str
    estimated_price: float
    model_url: str
    model_image: str


class CategorySchema(ModelSchema):
    class Meta:
        model = Category
        fields = '__all__'
        exclude = ['created_at', 'updated_at']

class ProductSchema(ModelSchema):
    category_name: str

    class Meta:
        model = Product
        fields = '__all__'
        exclude = ['created_at', 'updated_at']

    @staticmethod
    def resolve_category_name(obj):
        return obj.category.name

class AddToCartSchema(Schema):
    user: int
    product_id: int
    quantity: int

class AddToCartResponseSchema(Schema):
    user: int
    product_id: int
    quantity: int
    message:str

class CartItemSchema(Schema):
    cart_items: list
    total_price: float
    total_items: int

class UpdateCartItemSchema(Schema):
    quantity: int  