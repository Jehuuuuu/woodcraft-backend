from ninja import ModelSchema, Schema
from .models import CustomUser as User, CustomerDesign, Category, Product, CartItem, Order, CustomerAddress
from typing import List, Optional
import decimal

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
    is_best_seller: bool  

    class Meta:
        model = Product
        fields = '__all__'
        exclude = ['created_at', 'updated_at']

    @staticmethod
    def resolve_category_name(obj):
        return obj.category.name

    @staticmethod
    def resolve_is_best_seller(obj):
        return obj.is_best_seller
    
class AddProductSchema(Schema):
    id: Optional[int]  
    name: str
    description: Optional[str]
    price: float
    stock: Optional[int]
    featured: Optional[bool]
    image: Optional[str] 
    default_material: Optional[str]
    category_id: int  

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
    product_id : int | None = None
    cart_items: list
    total_price: float
    total_items: int

class UpdateCartItemSchema(Schema):
    quantity: int

class CheckoutSessionSchema(Schema):
    user_id: int
    currency: str
    success_url: str
    cancel_url: str

class CheckoutSessionResponseSchema(Schema):
    session_id: str | None = None
    url: str | None = None
    error: str | None = None

class OrderItemSchema(Schema):
    product_name: str
    quantity: int
    price: decimal.Decimal
    
    @staticmethod
    def resolve_product_name(obj):
        return obj.product.name if obj.product else None

class OrderSchema(Schema):
    order_id: int
    customer: str
    status: str
    address: str
    total_price: decimal.Decimal
    currency: str
    created_at: str
    updated_at: str
    items: List[OrderItemSchema]

    @staticmethod
    def resolve_user_id(obj):
        return obj.user.id

    @staticmethod
    def resolve_items(obj):
        return obj.items.all()

class UpdateOrderStatusSchema(Schema):
    status: str

class UpdateCustomerInfoSchema(Schema):
    first_name:str 
    last_name: str
    email: str
    phone_number: int = None
    address: str = None
    gender: str = None
    date_of_birth: str = None
    profile_picture: str = None

class CustomerAddressSchema(ModelSchema):
    class Meta: 
        model = CustomerAddress
        fields = '__all__'
        exclude = ['created_at', 'updated_at']