from ninja import NinjaAPI
from django.contrib.auth import login, authenticate, logout
from api.models import CustomUser as User
from django.middleware.csrf import get_token
from ninja.security import django_auth
from api.schemas import *
import logging
from api.ai_service import generate_3d_model
import os

api = NinjaAPI()
logger = logging.getLogger(__name__)

@api.get("/set-csrf-token")
def set_csrf_token(request):
    return {"csrf_token": get_token(request)}

@api.post("/login")
def login_view(request, payload: SignInSchema):
    user = authenticate(request, username = payload.email, password = payload.password)
    if user is not None:
        login(request, user)
        return {"success": True}
    return {"success": False, "message": "Invalid Credentials"}

@api.post("/logout", auth=django_auth)
def logout_view(request):
    logout(request)
    return {"message": "Logged out"}

@api.post("/register")
def register_view(request, payload: SignUpSchema):
    try:
        User.objects.create_user(username=payload.email, email=payload.email, first_name = payload.first_name, last_name = payload.last_name , password = payload.password)
        return {"success": "User registered successfully"}
    except Exception as e:
        return {"error": str(e)}

@api.get("/user", auth=django_auth)
def get_user(request):
    if request.user:
        return{
            "email": request.user.email,
            "firstName": request.user.first_name,
            "lastName": request.user.last_name
        }
    else:
        return{
            "message": "User not logged in"
        }

@api.post("/generate_3d_model")
def product_configurator(request, payload: CustomerDesignSchema):
    decoration_type_name = payload.decoration_type.replace('_', ' ').title() if payload.decoration_type else ''
    design_prompt = f"{decoration_type_name} {payload.design_description}"
    dimensions = {
                    'height': payload.height,
                    'width': payload.width,
                    'thickness':  payload.thickness
                }

    response_data = generate_3d_model(
        design_prompt=design_prompt,
        material=payload.material,
        dimensions=dimensions
    )
    
    # Check if 3D model generation was successful
    if not response_data:
        return {
            'success': False,
            'message': 'Failed to generate 3D model'
        }
    
    material_multipliers = {
        'oak': 1.5,
        'maple': 1.8,
        'pine': 0.7,
        'mahogany': 1.2,
        'walnut': 2.0
    }
    
    complexity_score = min(100, (len(payload.design_description) / 150) * 100)
    
    size_factor = (payload.height * payload.width * payload.thickness) / 1000
    
    base_price = 2500
    material_factor = material_multipliers.get(payload.material, 1.0)
    
    estimated_price = base_price * (complexity_score / 100) * material_factor * max(1, size_factor)
    
    # customer_design = CustomerDesign.objects.create(
    #     user=request.user,
    #     design_prompt=design_prompt,
    #     estimated_price=estimated_price,
    #     status='generated'
    # )

    production_days = int((complexity_score / 10) + (size_factor * 2)) + 5
    production_time = f"{production_days} days"
    if production_days > 14:
        production_weeks = (production_days + 6) // 7
        production_time = f"{production_weeks} weeks"

    return({
            'success': True,
            'estimated_price': float(estimated_price),
            'complexity_score': complexity_score,
            'production_time': production_time,
            'model_data': response_data,
            'message': '3D Model generated successfully'
        })

@api.get("/get_categories", response=list[CategorySchema])
def get_categories(request):
    categories = Category.objects.all()
    return categories   

@api.get("/get_products", response=list[ProductSchema])
def get_products(request):
    products = Product.objects.all()
    return products

@api.post("/categories", response=CategorySchema)
def create_category(request, payload: CategorySchema):
    category = Category.objects.create(**payload.dict())
    return category

@api.post("/products", response=ProductSchema)
def create_product(request, payload: ProductSchema):
    product = Product.objects.create(**payload.dict())
    return product