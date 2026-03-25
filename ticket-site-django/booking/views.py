from .models import Booking, Event, Seat, Waitlist
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect  # <--- CHANGED: Added redirect
from django.http import JsonResponse
import json
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.db import models


@csrf_exempt
@csrf_exempt
def lock_seats(request):
    """Lock seats for 5 minutes when user clicks them (AJAX call)"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            event_obj = get_active_event()
            if not event_obj:
                return JsonResponse({'success': False, 'error': 'No Event configured.'})

            seats_list = data.get('seats', [])

            # Enforce maximum 5 seats per booking
            if len(seats_list) > 5:
                return JsonResponse({'success': False, 'error': 'Maximum 5 seats can be booked at a time'})

            five_minutes_ago = timezone.now() - timedelta(minutes=5)
            locked = []
            failed = []
            for seat_id in seats_list:
                row = seat_id[0]
                number = int(seat_id[1:])
                try:
                    seat = Seat.objects.get(
                        event=event_obj, row=row, number=number)
                    is_stale_lock = (
                        seat.status == 'LOCKED' and
                        (not seat.lock_time or seat.lock_time < five_minutes_ago)
                    )

                    if is_stale_lock:
                        seat.status = 'AVAILABLE'
                        seat.lock_time = None

                    if seat.status == 'AVAILABLE':
                        seat.status = 'LOCKED'
                        seat.lock_time = timezone.now()
                        seat.save()
                        locked.append(seat_id)
                    else:
                        failed.append(seat_id)
                except Seat.DoesNotExist:
                    failed.append(seat_id)
            return JsonResponse({'success': True, 'locked': locked, 'failed': failed})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# --- 1. HOME PAGE ---


def index(request):
    # SET YOUR TOTAL CAPACITY HERE
    total_capacity = 300

    # 2. CALCULATE SOLD SEATS
    sold_data = Booking.objects.filter(
        status__iexact='confirmed').aggregate(Sum('quantity'))
    sold_count = sold_data['quantity__sum'] or 0

    # 3. CALCULATE REMAINING
    seats_left = total_capacity - sold_count

    # Prevent negative numbers
    if seats_left < 0:
        seats_left = 0

    # 4. CHECK IF SOLD OUT (New Logic)
    is_sold_out = (seats_left == 0)

    return render(request, 'booking/seat_map_general.html', {
        'seats_left': seats_left,
        'is_sold_out': is_sold_out,  # <--- CHANGED: Passed this to HTML
    })

# --- Helper: Get active event (prefer event with most seats) ---


def get_active_event():
    """Get the event with the most seats (active event for seating chart)"""
    from django.db.models import Count
    event = Event.objects.annotate(seat_count=Count(
        'seat')).order_by('-seat_count').first()
    return event if event else Event.objects.first()

# --- 2. SUBMIT BOOKING (Existing) ---


@csrf_exempt
def submit_manual_booking(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            event_obj = Event.objects.first()
            if not event_obj:
                return JsonResponse({'success': False, 'error': 'No Event configured.'})

            raw_phone = str(data['phone'])
            clean_phone = raw_phone.replace(
                " ", "").replace("+", "").replace("-", "")
            if len(clean_phone) > 10:
                clean_phone = clean_phone[-10:]

            booking = Booking.objects.create(
                event=event_obj,
                customer_name=data['name'],
                email=data['email'],
                phone=clean_phone,
                razorpay_payment_id=data['utr'],
                quantity=int(data.get('qty', 1)),
                status="PENDING",
                amount=0
            )

            return JsonResponse({'success': True})
        except Exception as e:
            print(f"Booking Error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})

# --- 3. SUBMIT WAITLIST (New Function) ---


def submit_waitlist(request):
    if request.method == "POST":
        name = request.POST.get('waitlist_name')
        phone = request.POST.get('waitlist_phone')

        # Save to database if data exists
        if name and phone:
            Waitlist.objects.create(name=name, phone=phone)

        # Create a simple success page or redirect back
        # Ideally, make a 'booking/waitlist_success.html' template
        return render(request, 'booking/waitlist_success.html')

    return redirect('index')


# --- 4. SEATING CHART PAGE ---
def seat_map_page(request):
    """Display the seating chart for booking specific seats"""
    event_obj = get_active_event()
    if not event_obj:
        return render(request, 'booking/seat_map_pick.html', {
            'booked_seats_json': json.dumps([]),
            'locked_seats_json': json.dumps([])
        })

    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    five_minutes_ago = now - timedelta(minutes=5)

    # Get BOOKED seats (confirmed, red)
    booked_seats = Seat.objects.filter(
        event=event_obj,
        status='BOOKED'
    ).values_list('row', 'number')

    # Get LOCKED seats (payment in progress, black) - only recent ones
    locked_seats = Seat.objects.filter(
        event=event_obj,
        status='LOCKED',
        lock_time__gte=five_minutes_ago
    ).values_list('row', 'number')

    booked_seat_ids = [f"{row}{number}" for row, number in booked_seats]
    locked_seat_ids = [f"{row}{number}" for row, number in locked_seats]

    return render(request, 'booking/seat_map_pick.html', {
        'booked_seats_json': json.dumps(booked_seat_ids),
        'locked_seats_json': json.dumps(locked_seat_ids),
        'event': event_obj
    })


# --- 5. SUBMIT SEAT BOOKING (Manual Payment) ---
@csrf_exempt
def submit_seat_booking(request):
    """Submit seat booking with manual payment (like FCFS)"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            event_obj = get_active_event()
            if not event_obj:
                return JsonResponse({'success': False, 'error': 'No Event configured.'})

            seats_list = data.get('seats', [])
            name = data.get('name', '')
            email = data.get('email', '')
            phone = data.get('phone', '')
            utr = data.get('utr', '')

            print(
                f"DEBUG: Received booking request - name={name}, email={email}, phone={phone}, seats={seats_list}, utr={utr}")
            print(
                f"DEBUG: Active event: {event_obj.name} (ID: {event_obj.id})")

            if not seats_list or not name or not email or not phone or not utr:
                return JsonResponse({'success': False, 'error': 'Missing required fields'})

            # Enforce maximum 5 seats per booking
            if len(seats_list) > 5:
                return JsonResponse({'success': False, 'error': 'Maximum 5 seats can be booked at a time'})

            # Validate seats: allow AVAILABLE or recently LOCKED (from Pay Now flow)

            # Validate seats: allow AVAILABLE or recently LOCKED (from Pay Now flow)
            seat_objects = []
            now = timezone.now()
            five_minutes_ago = now - timedelta(minutes=5)
            for seat_id in seats_list:
                row = seat_id[0]
                number = int(seat_id[1:])

                try:
                    seat = Seat.objects.get(
                        event=event_obj, row=row, number=number)
                    is_recently_locked = (
                        seat.status == 'LOCKED' and
                        seat.lock_time and
                        seat.lock_time >= five_minutes_ago
                    )

                    if seat.status != 'AVAILABLE' and not is_recently_locked:
                        print(
                            f"DEBUG: Seat {seat_id} not available (status: {seat.status})")
                        return JsonResponse({
                            'success': False,
                            'error': f'Seat {seat_id} is no longer available'
                        })
                    seat_objects.append(seat)
                except Seat.DoesNotExist:
                    print(
                        f"DEBUG: Seat {seat_id} not found in event {event_obj.id}")
                    return JsonResponse({'success': False, 'error': f'Seat {seat_id} not found'})

            # Create booking (PENDING - waiting for admin verification)
            raw_phone = str(phone)
            clean_phone = raw_phone.replace(
                " ", "").replace("+", "").replace("-", "")
            if len(clean_phone) > 10:
                clean_phone = clean_phone[-10:]

            booking = Booking.objects.create(
                event=event_obj,
                customer_name=name,
                email=email,
                phone=clean_phone,
                razorpay_payment_id=utr,
                quantity=len(seats_list),
                status="PENDING",
                amount=calculate_seat_price(seats_list)
            )

            # Add seats to booking and mark as BOOKED immediately after submit
            for seat in seat_objects:
                booking.seats.add(seat)
                seat.status = 'BOOKED'
                seat.lock_time = None
                seat.save()

            print(f"DEBUG: Booking created successfully - ID: {booking.id}")
            print(f"DEBUG: {len(seat_objects)} seats marked as BOOKED")
            return JsonResponse({'success': True, 'booking_id': booking.id})
        except Exception as e:
            print(f"ERROR: Seat Booking Error: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


def calculate_seat_price(seats_list):
    """Calculate total price for selected seats based on row"""
    TOP_PRICE = 350    # rows A–F
    BOTTOM_PRICE = 250  # rows G–P

    total = 0
    for seat_id in seats_list:
        row = seat_id[0]
        if row in "ABCDEFG":
            total += TOP_PRICE
        else:
            total += BOTTOM_PRICE

    return total
