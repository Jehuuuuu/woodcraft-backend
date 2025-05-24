from ninja import NinjaAPI
from django.contrib.auth import login, authenticate, logout
from api.models import CustomUser as User
from api. models import *
from django.middleware.csrf import get_token
from ninja.security import django_auth
from api.schemas import *
import logging
from api.ai_service import initiate_task_id, poll_task_status
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.http import HttpResponse
from django.http import JsonResponse as JSONResponse
import stripe
from django.conf import settings
import os
from dotenv import load_dotenv
import requests
from decimal import Decimal

load_dotenv()
logger = logging.getLogger(__name__)

api = NinjaAPI(csrf=True)
FIXER_API_KEY = os.getenv("FIXER_API_KEY")
FIXER_API_URL = f"http://data.fixer.io/api/latest?access_key={FIXER_API_KEY}&base=EUR"

@api.post("/csrf")
@ensure_csrf_cookie
@csrf_exempt
def get_csrf_token(request):
    return HttpResponse('CSRF token set', status=200)

@api.get("/set-csrf-token")
def set_csrf_token(request):
    return {"csrf_token": get_token(request)}

@api.post("/login")
def login_view(request, payload: SignInSchema):
    user = authenticate(request, username = payload.email, password = payload.password)
    if user is not None:
        if user.is_superuser:
            login(request, user)
            user_data = {
                "email": user.email,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "is_admin": True
            }
            response = JSONResponse({"success": True,
                    "user": user_data}
            )
            return response
        else:
            login(request, user)
            user_data = {
                "email": user.email,
                "firstName": user.first_name,
                "lastName": user.last_name
            }
            response = JSONResponse({"success": True,
                    "user": user_data}
            )
            return response
    return {"success": False, "message": "Invalid Credentials"}

@api.post("/logout", auth=django_auth)
def logout_view(request):
    logout(request)
    return {"message": "Logged out"}

@api.post("/register")
def register_view(request, payload: SignUpSchema):
    try:
        user = User.objects.create_user(username=payload.email, email=payload.email, first_name = payload.first_name, last_name = payload.last_name , password = payload.password)
        cart = Cart.objects.create(user=user)

        return {"success": "User registered successfully",
                "cart": cart.user.email}
    except Exception as e:
        return {"error": str(e)}

@api.get("/user", auth=django_auth)
def get_user(request):
    user = request.user
    if user:
        if user.is_superuser:
            return {
                "success": True,
                "id": request.user.id,
                "email": request.user.email,
                "firstName": request.user.first_name,
                "lastName": request.user.last_name,
                "is_admin": True
            }
        else:
            return{ 
                "success": True,
                "id": request.user.id,
                "email": request.user.email,
                "firstName": request.user.first_name,
                "lastName": request.user.last_name,
                "is_admin": False
            }
    else:
        return{
            "message": "User not logged in"
        }

@api.post("/initiate_task_id")
def product_configurator(request, payload: CustomerDesignSchema):
    decoration_type_name = payload.decoration_type.replace('_', ' ').title() if payload.decoration_type else ''
    design_prompt = f"{decoration_type_name} {payload.design_description}"
    dimensions = {
                    'height': payload.height,
                    'width': payload.width,
                    'thickness':  payload.thickness
                }

    response_data = initiate_task_id(
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
            'task_id': response_data.get('task_id'),
            'message': 'Model generation started successfully',
        })

@api.get("/get_task_status/{task_id}")
def get_task_status(request, task_id):
    response_data = poll_task_status(task_id)
    
    if not response_data:
        return {
            'success': False,
            'message': 'Failed to retrieve task status'
        }
    
    if response_data.get('status') == 'success':
        return {
            'success': True,
            'task_id': task_id,
            'task_status': "Success",
            'message': 'Task completed successfully',
            'data': response_data
        }
    
    return {
        'success': False,
        'task_id': task_id,
        'task_status': "Generating",
        'message': 'Task is still in progress',
        'data': response_data
    }

@api.post("/create_design")
def create_customer_design(request, payload: CreateCustomerDesignSchema):
    customer_design = CustomerDesign.objects.create(
        user = CustomUser.objects.get(id=payload.user_id),
        design_description=payload.design_description,
        width=payload.width,
        height=payload.height,
        thickness=payload.thickness,
        decoration_type=payload.decoration_type,
        material=payload.material,
        model_url=payload.model_url,
        model_image=payload.model_image,
        estimated_price=payload.estimated_price,
        status='pending',
    )
    return {
        "success": True,
        "message": "Customer design created successfully",
    }

@api.get("/get_customer_designs", response=list[FetchCustomerDesignsSchema])
def get_customer_designs(request, user: int):
    try:
        customer_designs = CustomerDesign.objects.filter(user=user)
        return customer_designs
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve customer designs",
        }

@api.get("/get_all_customer_designs", response=list[FetchCustomerDesignsSchema])
def get_all_customer_designs(request):
    try:
        customer_designs = CustomerDesign.objects.all()
        return customer_designs
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve customer designs",
        }

@api.put("/approve_design/{design_id}")
def approve_design(request, design_id: int, payload: ApproveDesignSchema):
    try:
        customer_design = CustomerDesign.objects.get(id=design_id)
        customer_design.status = 'approved'
        customer_design.final_price = payload.final_price
        customer_design.save()
        return {
            "success": True,
            "message": "Customer design approved successfully",
        }
    except CustomerDesign.DoesNotExist:
        return {
            "success": False,
            "error": "Customer design not found",
            "message": "Failed to approve customer design",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to approve customer design",
        }
    
@api.put("/reject_design/{design_id}")
def reject_design(request, design_id: int, payload: RejectDesignSchema):
    try:
        customer_design = CustomerDesign.objects.get(id=design_id)
        customer_design.status = 'rejected'
        customer_design.notes = payload.message
        customer_design.save()
        return {
            "success": True,
            "message": "Customer design rejected successfully",
        }
    except CustomerDesign.DoesNotExist:
        return {
            "success": False,
            "error": "Customer design not found",
            "message": "Failed to reject customer design",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to reject customer design",
        }

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

@api.post("add_to_cart", response=AddToCartResponseSchema)
def add_to_cart(request, payload: AddToCartSchema):
    try:
        # Get the user and their cart
        user = CustomUser.objects.get(id=payload.user)
        cart = Cart.objects.get(user=user)
        product = Product.objects.get(id=payload.product_id)
        quantity = payload.quantity

        # Check if the product already exists in the cart
        existing_items = CartItem.objects.filter(cart=cart, product=product)

        if existing_items.exists():
            # If duplicates exist, sum their quantities
            total_quantity = quantity + sum(item.quantity for item in existing_items)

            # Keep the first cart item and update its quantity
            primary_item = existing_items.first()
            primary_item.quantity = total_quantity
            primary_item.save()

            # Delete the other duplicate items
            existing_items.exclude(id=primary_item.id).delete()

            return {
                "user": payload.user,
                "product_id": payload.product_id,
                "quantity": total_quantity,
                "message": "Merged duplicate items in the cart",
            }
        else:
            # If no duplicates, create a new cart item
            added_to_cart = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
            )
            return {
                "user": payload.user,
                "product_id": payload.product_id,
                "quantity": added_to_cart.quantity,
                "message": "Item added to cart",
            }
    except Exception as e:
        return {"error": str(e)}
    
@api.post("add_design_to_cart", response=AddToCartResponseSchema)
def add_design_to_cart(request, payload: AddToCartSchema):
    try:
        # Get the user and their cart
        user = CustomUser.objects.get(id=payload.user)
        cart = Cart.objects.get(user=user)
        design = CustomerDesign.objects.get(id=payload.design_id)
        quantity = payload.quantity

        add_to_cart = CartItem.objects.create(
                cart=cart,
                customer_design=design,
                quantity=quantity,
            )
        design.is_added_to_cart = True
        design.save()
        return {
                "user": payload.user,
                "product_id": payload.design_id,
                "quantity": add_to_cart.quantity,
                "message": "Item added to cart",
            }
    except Exception as e:
        return {"error": str(e)}

@api.get("/cart", response=CartItemSchema)
def get_cart(request, user: int):
    try:
        cart = Cart.objects.get(user=user)
        cart_items = CartItem.objects.filter(cart=cart)
        
        cart_items_list = []
        total_price = 0
        total_items = 0
        
        for item in cart_items:
            cart_item_dict = {
                "cart_item_id_num": item.id,
                "quantity": item.quantity,
            }
            
            # Handle regular products
            if item.product:
                cart_item_dict.update({
                    "product_name": item.product.name,
                    "product_image": item.product.image.url if item.product.image else None,
                    "price": float(item.product.price),
                    "total_price": float(item.product.price * item.quantity),
                    "customer_design": None,
                    "material": None,
                    "final_price": None,
                })
                total_price += item.product.price * item.quantity
            
            # Handle customer designs
            if item.customer_design:
                cart_item_dict.update({
                    "product_name": f"Custom Design - {item.customer_design.design_description}",
                    "product_image": None,
                    "price": float(item.customer_design.final_price) if item.customer_design.final_price else float(item.customer_design.estimated_price),
                    "total_price": float(item.customer_design.final_price * item.quantity) if item.customer_design.final_price else float(item.customer_design.estimated_price * item.quantity),
                    "customer_design": item.customer_design.design_description,
                    "material": item.customer_design.material,
                    "final_price": float(item.customer_design.final_price) if item.customer_design.final_price else None,
                })
                total_price += (item.customer_design.final_price * item.quantity) if item.customer_design.final_price else (item.customer_design.estimated_price * item.quantity)
            
            cart_items_list.append(cart_item_dict)
            total_items += item.quantity

        return {
            "cart_items": cart_items_list,
            "total_price": float(total_price),
            "total_items": total_items,
        }
    
    except Cart.DoesNotExist:
        return {"error": "Cart not found"}
    except Exception as e:
        return {"error": str(e)}
    
@api.put("/update_cart_item/{cart_item_id}")
def update_cart_item(request, cart_item_id: int, payload: UpdateCartItemSchema):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
        cart_item.quantity = payload.quantity  
        cart_item.save()
        return {"message": "Cart item updated successfully"}
    except CartItem.DoesNotExist:
        return {"error": "Cart item not found"}
    except Exception as e:
        return {"error": str(e)}

@api.delete("/delete_cart_item/{cart_item_id}")
def delete_cart_item(request, cart_item_id: int):
    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
        if cart_item.customer_design:
            design = cart_item.customer_design
            design.is_added_to_cart = False
            design.save()
            cart_item.delete()
        else:
            cart_item.delete()
        return {"message": "Cart item deleted successfully"}
    except CartItem.DoesNotExist:
        return {"error": "Cart item not found"}
    except Exception as e:
        return {"error": str(e)}

 
def get_exchange_rate(currency: str) -> float:
    params = {
        "access_key": FIXER_API_KEY,
        "symbols": "PHP," + currency.upper(),
    }
    resp = requests.get(FIXER_API_URL, params=params)
    data = resp.json()
    if not data.get("success"):
        raise Exception("Failed to fetch exchange rates")

    rates = data["rates"]
    rate_php = rates["PHP"]    
    rate_target = rates[currency.upper()]    

    conversion_rate = rate_target / rate_php

    return float(conversion_rate)

@api.post("/create-checkout-session")
def create_checkout_session(request, payload: CheckoutSessionSchema):
    try:
        user = CustomUser.objects.get(id=payload.user_id)
        cart = Cart.objects.get(user=user)
        cart_items = CartItem.objects.filter(cart=cart)

        currency = payload.currency.lower()
        if currency == "PHP" or currency == "php":
            exchange_rate = 1
        else:
            exchange_rate = get_exchange_rate(currency)

        if not cart_items:
            return CheckoutSessionResponseSchema(error="Cart is empty")

        line_items = []
        for item in cart_items:
            if item.product:
                image_url = f"https://woodcraft-backend.onrender.com{item.product.image.url}"
                unit_amount = int(item.product.price * Decimal(str(exchange_rate)) * 100)
                line_items.append({
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': item.product.name,
                            'images': [image_url],
                        },
                        'unit_amount': unit_amount,
                    },
                    'quantity': item.quantity,
                })
            elif item.customer_design:
                price = item.customer_design.final_price or item.customer_design.estimated_price
                unit_amount = int(price * Decimal(str(exchange_rate)) * 100)
                line_items.append({
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': f'Custom Design - {item.customer_design.design_description}',
                            'images': [item.customer_design.model_image] if item.customer_design.model_image else [],
                        },
                        'unit_amount': unit_amount,
                    },
                    'quantity': item.quantity,
                })

        if not line_items:
            return CheckoutSessionResponseSchema(error="No valid items in cart")

        session = stripe.checkout.Session.create(
            customer_email=user.email,
            payment_method_types=['card'],
            billing_address_collection='required',
            shipping_address_collection={'allowed_countries': ['PH', 'US', 'CA']},
            line_items=line_items,
            mode='payment',
            currency=currency,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
            metadata={'user_id': user.id, 'currency': currency},
        )

        return CheckoutSessionResponseSchema(session_id=session.id, url=session.url)

    except CustomUser.DoesNotExist:
        return CheckoutSessionResponseSchema(error="User not found")
    except Cart.DoesNotExist:
        return CheckoutSessionResponseSchema(error="Cart not found")
    except stripe.error.StripeError as e:
        return CheckoutSessionResponseSchema(error=str(e))
    except Exception as e:
        return CheckoutSessionResponseSchema(error=f"An unexpected error occurred: {e}")