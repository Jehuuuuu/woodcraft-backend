from ninja import ModelSchema, Schema
from .models import CustomUser as User, CustomerDesign, Category, Product

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
        fields = ['name']

class ProductSchema(ModelSchema):
    class Meta:
        model = Product
        fields = '__all__'
        exclude = ['created_at', 'updated_at']