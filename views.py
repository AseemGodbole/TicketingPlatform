from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
import json
import razorpay
import csv

from .models import Event, Seat, Booking

# Initialize Razorpay Client
razor_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# ==========================================
# 1. PAYMENT VERIFICATION & EMAIL
# ==========================================

# Make sure these are imported at the top of views.py
# from django.conf import settings
# from django.core.mail import send_mail
# from .models import Booking, Seat


def verify_payment(request):
    data = json.loads(request.body)
    booking_id = data.get("booking_id")

    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({"status": "fail", "error": "Booking not found"}, status=404)

    # 1. Verify Signature (SECURITY CHECK)
    params_dict = {
        "razorpay_order_id": data.get("razorpay_order_id"),
        "razorpay_payment_id": data.get("razorpay_payment_id"),
        "razorpay_signature": data.get("razorpay_signature")
    }

    try:
        razor_client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        # Verification Failed -> Fail the booking
        booking.status = "FAILED"
        booking.save()

        # FIX 1: Use Seat.objects.filter to safely unlock seats
        Seat.objects.filter(booking=booking).update(
            status="AVAILABLE", lock_time=None)

        return JsonResponse({"status": "fail", "error": "Signature mismatch"}, status=400)

    # 2. Verification Success -> Save Data
    booking.status = "SUCCESS"
    booking.razorpay_payment_id = params_dict["razorpay_payment_id"]
    booking.save()

    # FIX 2: Use Seat.objects.filter to safely mark seats as BOOKED
    Seat.objects.filter(booking=booking).update(
        status="BOOKED", lock_time=None)

    # 3. SEND CONFIRMATION EMAIL
    try:
        # FIX 3: Count seats safely to avoid "AttributeError"
        ticket_count = Seat.objects.filter(booking=booking).count()

        subject = "Booking Confirmation - Auditorium Event"
        message = (
            # Changed customer_name to name
            f"Dear {booking.customer_name},\n\n"
            f"Your booking is confirmed!\n\n"
            f"--------------------------------\n"
            f"VENUE:  Main Auditorium, City Center\n"
            f"TIME:   7:00 PM, Saturday\n"
            f"SEATS:  {ticket_count}\n"        # Used safe variable
            # Changed amount to total_amount
            f"PAID:   Rs. {booking.amount}\n"
            f"--------------------------------\n\n"
            f"Please show this email at the entrance.\n"
            f"Booking ID: #{booking.id}\n\n"
            f"Thank you!"
        )

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [booking.email],
            fail_silently=False,
        )
        print(f"Email sent to {booking.email}")
    except Exception as e:
        print(f"Email failed: {e}")
        # We don't fail the request if email fails, payment is already done.

    return JsonResponse({"status": "ok"})


@require_POST
def unlock_seats(request):
    """
    Releases locked seats if payment is cancelled or fails.
    """
    try:
        data = json.loads(request.body)
        booking_id = data.get("booking_id")
        seats = data.get("seats", [])

        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id)
                booking.status = "FAILED"
                booking.save()
            except Booking.DoesNotExist:
                pass

        event = Event.objects.first()
        for sid in seats:
            # Parse ID like "A1"
            row = sid[0]
            num = int(sid[1:])
            Seat.objects.filter(
                event=event,
                row=row,
                number=num,
                status="LOCKED"
            ).update(status="AVAILABLE", lock_time=None)

        return JsonResponse({"status": "ok"})
    except Exception as e:
        print(f"Error unlocking seats: {e}")
        return JsonResponse({"status": "error"}, status=500)


# ==========================================
# 2. GENERAL ADMISSION LOGIC (QUANTITY)
# ==========================================

@ensure_csrf_cookie
def seat_map_general(request):
    event = Event.objects.first()

    # Auto-cleanup stale seats
    if event:
        locked_seats = Seat.objects.filter(event=event, status="LOCKED")
        for seat in locked_seats:
            if seat.is_stale():
                seat.status = "AVAILABLE"
                seat.lock_time = None
                seat.save()

    # Get all non-available seats for visual markers
    seats = Seat.objects.filter(event=event).exclude(status="AVAILABLE")
    booked_list = [f"{s.row}{s.number}" for s in seats]

    return render(request, "booking/seat_map_general.html", {
        "booked_seats_json": booked_list,
        "event": event
    })


@require_POST
def create_order_general(request):
    data = json.loads(request.body)
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")

    try:
        qty = int(data.get("qty", 0))
    except ValueError:
        qty = 0

    if qty < 1 or qty > 10:
        return JsonResponse({"error": "Invalid quantity (1-10 allowed)"}, status=400)

    event = Event.objects.first()
    if not event:
        return JsonResponse({"error": "No event configured"}, status=400)

    price_per_ticket = 200
    total_amount = qty * price_per_ticket

    with transaction.atomic():
        # Find next available seats
        available_seats = Seat.objects.select_for_update().filter(
            event=event,
            status="AVAILABLE"
        ).order_by('row', 'number')[:qty]

        if len(available_seats) < qty:
            return JsonResponse({
                "error": f"Not enough seats! Only {len(available_seats)} remaining."
            }, status=400)

        chosen_seats = []
        now = timezone.now()
        for seat in available_seats:
            seat.status = "LOCKED"
            seat.lock_time = now
            seat.save()
            chosen_seats.append(seat)

        # Create Booking
        booking = Booking.objects.create(
            event=event,
            customer_name=name,
            email=email,
            phone=phone,
            amount=total_amount,
            status="PENDING"
        )
        booking.seats.set(chosen_seats)

        # Create Razorpay Order
        razor_order = razor_client.order.create(
            dict(amount=total_amount * 100, currency="INR", payment_capture=1)
        )
        booking.razorpay_order_id = razor_order["id"]
        booking.save()

    return JsonResponse({
        "order_id": razor_order["id"],
        "amount": total_amount * 100,
        "booking_id": booking.id,
        "key_id": settings.RAZORPAY_KEY_ID,
        "assigned_seats": [f"{s.row}{s.number}" for s in chosen_seats]
    })


# ==========================================
# 3. EXCEL EXPORT (ADMIN)
# ==========================================

def export_bookings_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="booking_log.csv"'

    writer = csv.writer(response)
    # The Columns
    writer.writerow(['Booking ID', 'Name', 'Email', 'Phone',
                     'Qty', 'Total Paid', 'Date', 'Payment ID'])

    bookings = Booking.objects.filter(status="SUCCESS").values_list(
        'id', 'customer_name', 'email', 'phone', 'qty', 'amount', 'created_at', 'razorpay_payment_id'
    )
    for booking in bookings:
        writer.writerow(booking)

    return response


# ==========================================
# 4. RESET TOOL (FIXED)
# ==========================================

def magic_reset(request):
    # 1. Clear Database
    Seat.objects.all().delete()
    Booking.objects.all().delete()
    Event.objects.all().delete()

    # 2. Create Event
    event = Event.objects.create(
        name="Movie Night",
        date="2025-01-01",
        time="18:00",
        venue="Auditorium",
        top_price=200,
        bottom_price=200
    )

    # 3. Create EXACTLY 90 Seats (Rows A-I, 1-10)
    seats = []
    for r in "ABCDEFGHI":  # 9 Rows
        for n in range(1, 11):  # 10 Seats per row
            seats.append(
                Seat(event=event, row=r, number=n, status="AVAILABLE"))
    Seat.objects.bulk_create(seats)

    return HttpResponse("Reset Successful. 90 Seats are now available. <a href='/'>Go Back</a>")
