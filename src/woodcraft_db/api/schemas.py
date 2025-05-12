from ninja import ModelSchema, Schema
from .models import CustomUser as User, CustomerDesign, Category, Product, CartItem
from typing import Optional

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
    width: float
    height: float
    thickness: float
    estimated_price: float
    model_url: str
    model_image: str
    status:str
    notes: str = None
    final_price: float = None

class FetchCustomerDesignsSchema(ModelSchema):
    name: str
    dimensions: str
    final_price: Optional[float]
    class Meta:
        model = CustomerDesign
        fields = '__all__'
        exclude = ['created_at', 'updated_at']
    @staticmethod
    def resolve_name(obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    @staticmethod
    def resolve_dimensions(obj):
        return f"{obj.width} x {obj.height} x {obj.thickness}"

class ApproveDesignSchema(Schema):
    final_price: float

class RejectDesignSchema(Schema):
    message:str

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
    product_id: int = None
    design_id: int = None
    quantity: int

class AddToCartResponseSchema(Schema):
    user: int
    product_id: int = None
    design_id: int = None
    quantity: int
    message:str

class CartItemSchema(Schema):
    cart_items: list
    total_price: float
    total_items: int

class UpdateCartItemSchema(Schema):
    quantity: int

class CheckoutSessionSchema(Schema):
    user_id: int
    success_url: str
    cancel_url: str

class CheckoutSessionResponseSchema(Schema):
    session_id: str | None = None
    url: str | None = None
    error: str | None = None