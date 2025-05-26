from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import stripe
from django.conf import settings
from .models import Cart, CartItem, Order, CustomUser, Product, OrderItem, CustomerDesign
from decimal import Decimal
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