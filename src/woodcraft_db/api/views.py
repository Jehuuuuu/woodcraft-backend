from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import stripe
from django.conf import settings
from .models import Cart, CartItem, Order, CustomUser

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
            currency = session.metadata.get("currency")
            total_price=session.amount_total / 100,
            address = f"{session.shipping_details.address.line1}, {session.shipping_details.address.city}, {session.shipping_details.address.state}, {session.shipping_details.address.country}, {session.shipping_details.address.postal_code}"
            if user_id:
                CartItem.objects.filter(cart__user_id=user_id).delete()
                user = CustomUser.objects.get(id=user_id)
                Order.objects.create(
                    user=user,
                    total_price=total_price,
                    address=address,
                    currency=currency,
                    status="pending",
                )

        return JsonResponse({"success": True})

    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)