from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import stripe
from django.conf import settings
from .models import Cart, CartItem, Order, CustomUser, Product, OrderItem, CustomerDesign
from decimal import Decimal
import json
from api.ai_service import initiate_task_id

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )

        if event.type == "checkout.session.completed":
            session = event.data.object
            user_id = session.metadata.get("user_id")
            currency = session.metadata.get("currency").upper()
            total_price=Decimal(session.amount_total / 100)
            address = f"{session.shipping_details.address.line1}, {session.shipping_details.address.city}, {session.shipping_details.address.state}, {session.shipping_details.address.country}, {session.shipping_details.address.postal_code}"
            if user_id:
                
                user = CustomUser.objects.get(id=user_id)
                order = Order.objects.create(
                    user=user,
                    total_price=total_price,
                    address=address,
                    currency=currency,
                    status="pending",
                )
                line_items = stripe.checkout.Session.list_line_items(session.id, limit=100)
                for item in line_items.data:
                        try:
                            unit_price = Decimal(item.amount_total / (item.quantity * 100))
                        # Check if this is a custom design by looking at the name prefix
                            if item.description.startswith('Custom Design -'):

                                design_description = item.description.replace('Custom Design - ', '')
                                customer_design = CustomerDesign.objects.get(
                                    user=user,
                                    design_description=design_description
                                )
                                
                                order_item = OrderItem.objects.create(
                                    order=order,
                                    customer_design=customer_design,
                                    product=None,  # No product for custom designs
                                    quantity=item.quantity,
                                    price=unit_price,
                                )
                            else:
                                # Regular product
                                product = Product.objects.get(name=item.description)
                                order_item = OrderItem.objects.create(
                                    order=order,
                                    product=product,
                                    customer_design=None,  # No custom design for regular products
                                    quantity=item.quantity,
                                    price=unit_price,
                                )
                        except CustomerDesign.DoesNotExist:
                          print(f"CustomerDesign not found for description: {design_description}")
                          continue
                        except Product.DoesNotExist:
                            print(f"Product not found for description: {item.description}")
                            continue

                CartItem.objects.filter(cart__user_id=user_id).delete()

        return JsonResponse({"success": True})

    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def product_configurator(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body)  # Parse JSON payload
            decoration_type_name = payload.get("decoration_type", "").replace('_', ' ').title()
            design_prompt = f"{decoration_type_name} {payload.get('design_description', '')}"
            dimensions = {
                'height': payload.get('height'),
                'width': payload.get('width'),
                'thickness': payload.get('thickness')
            }

            response_data = initiate_task_id(
                design_prompt=design_prompt,
                material=payload.get('material'),
                dimensions=dimensions
            )

            if not response_data:
                return JsonResponse({
                    'success': False,
                    'message': 'Failed to generate 3D model'
                })

            material_multipliers = {
                'oak': 1.5,
                'maple': 1.8,
                'pine': 0.7,
                'mahogany': 1.2,
                'walnut': 2.0
            }

            complexity_score = min(100, (len(payload.get('design_description', '')) / 150) * 100)
            size_factor = (payload.get('height', 0) * payload.get('width', 0) * payload.get('thickness', 0)) / 1000
            base_price = 2500
            material_factor = material_multipliers.get(payload.get('material'), 1.0)
            estimated_price = base_price * (complexity_score / 100) * material_factor * max(1, size_factor)

            production_days = int((complexity_score / 10) + (size_factor * 2)) + 5
            production_time = f"{production_days} days"
            if production_days > 14:
                production_weeks = (production_days + 6) // 7
                production_time = f"{production_weeks} weeks"

            return JsonResponse({
                'success': True,
                'estimated_price': float(estimated_price),
                'complexity_score': complexity_score,
                'production_time': production_time,
                'task_id': response_data.get('task_id'),
                'message': 'Model generation started successfully',
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)