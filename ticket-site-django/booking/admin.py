from django.contrib import admin
from django.contrib.admin import AdminSite
from django.core.mail import send_mail
from django.conf import settings
from .models import Event, Seat, Booking, Waitlist
from django.db.models import Sum, Count, Q
import csv
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta


# --- CUSTOM ADMIN SITE WITH LIVE STATS ---
class CustomAdminSite(AdminSite):
    site_header = "Geet Ramayan - Admin Panel"
    site_title = "Ticket Management"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        """Add live seat statistics to admin dashboard"""
        from django.contrib.admin.views.decorators import staff_member_required
        from django.template.response import TemplateResponse
        five_minutes_ago = timezone.now() - timedelta(minutes=5)

        # Get active event
        from django.db.models import Count
        active_event = Event.objects.annotate(
            seat_count=Count('seat')).order_by('-seat_count').first()

        if active_event:
            # Calculate statistics
            total_seats = Seat.objects.filter(event=active_event).count()

            # Split counts so dashboard is explicit
            booked_seats = Seat.objects.filter(
                event=active_event,
                status='BOOKED'
            ).count()

            locked_seats = Seat.objects.filter(
                event=active_event,
                status='LOCKED',
                lock_time__gte=five_minutes_ago
            ).count()

            available_seats = Seat.objects.filter(
                event=active_event,
                status='AVAILABLE'
            ).count()

            # Booking stats
            total_bookings = Booking.objects.filter(event=active_event).count()
            pending_bookings = Booking.objects.filter(
                event=active_event, status='PENDING').count()
            confirmed_bookings = Booking.objects.filter(
                event=active_event, status='CONFIRMED').count()

            stats = {
                'event_name': active_event.name,
                'total_seats': total_seats,
                'booked_seats': booked_seats,
                'locked_seats': locked_seats,
                'sold_seats': booked_seats,
                'available_seats': available_seats,
                'total_bookings': total_bookings,
                'pending_bookings': pending_bookings,
                'confirmed_bookings': confirmed_bookings,
            }
        else:
            stats = {}

        extra_context = extra_context or {}
        extra_context['stats'] = stats

        return super().index(request, extra_context)


# Replace default admin site
admin.site.__class__ = CustomAdminSite
admin.site.site_header = "Geet Ramayan - Admin Panel"
admin.site.site_title = "Ticket Management"
admin.site.index_title = "Dashboard"


# --- SEAT ADMIN ---


@admin.action(description="Mark selected seats as BOOKED")
def mark_as_booked(modeladmin, request, queryset):
    queryset.update(status="BOOKED", lock_time=None)


@admin.action(description="Mark selected seats as AVAILABLE")
def mark_as_available(modeladmin, request, queryset):
    queryset.update(status="AVAILABLE", lock_time=None)


@admin.action(description="Release stale LOCKED seats (>5 min)")
def release_stale_locked_seats(modeladmin, request, queryset):
    cutoff = timezone.now() - timedelta(minutes=5)
    updated = Seat.objects.filter(status="LOCKED", lock_time__lt=cutoff).update(
        status="AVAILABLE", lock_time=None)
    modeladmin.message_user(
        request, f"Released {updated} stale locked seat(s).")


@admin.action(description="Release ALL stale LOCKED seats NOW")
def release_all_stale_locked_seats_now(modeladmin, request, queryset):
    """Release all stale LOCKED seats immediately (ignores selection)"""
    cutoff = timezone.now() - timedelta(minutes=5)
    updated = Seat.objects.filter(status="LOCKED", lock_time__lt=cutoff).update(
        status="AVAILABLE", lock_time=None)
    modeladmin.message_user(
        request, f"Released {updated} stale locked seat(s) immediately.")


def release_stale_locks_background():
    """Background function to release stale locks - only releases abandoned locks without pending bookings"""
    from booking.models import Booking

    cutoff = timezone.now() - timedelta(minutes=5)
    stale_locked_seats = Seat.objects.filter(
        status="LOCKED", lock_time__lt=cutoff)

    updated_count = 0
    for seat in stale_locked_seats:
        # Check if there's a pending booking for this seat
        has_pending_booking = Booking.objects.filter(
            seats__id=seat.id, status='PENDING').exists()

        if not has_pending_booking:
            # No pending booking = payment was abandoned, safe to release
            seat.status = "AVAILABLE"
            seat.lock_time = None
            seat.save()
            updated_count += 1

    if updated_count > 0:
        print(
            f"[Manual Release] Released {updated_count} abandoned locked seat(s) at {timezone.now()}")


class SeatAdmin(admin.ModelAdmin):
    list_display = ("event", "row", "number", "status")
    list_filter = ("status", "row")
    actions = [mark_as_booked, mark_as_available,
               release_stale_locked_seats, release_all_stale_locked_seats_now]


admin.site.register(Seat, SeatAdmin)


@admin.action(description='Export Selected Bookings to CSV')
def export_bookings_to_csv(modeladmin, request, queryset):
    # 1. Setup the response to be a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="confirmed_bookings.csv"'

    writer = csv.writer(response)

    # 2. Write the Header Row
    writer.writerow(['Customer Name', 'Status', 'Quantity',
                    'Phone', 'Email', 'Payment ID'])

    # 3. Write the Data Rows
    for booking in queryset:
        writer.writerow([
            booking.customer_name,
            booking.status,
            booking.quantity,
            booking.phone,
            booking.email,
            booking.razorpay_payment_id,
        ])

    return response

# --- BOOKING ADMIN ---
@admin.action(description='🔄 Resend Confirmation Email')
def resend_confirmation_emails(modeladmin, request, queryset):
    """Resend confirmation emails for selected bookings"""
    from .emails import send_booking_confirmed_email

    success_count = 0
    failure_count = 0

    for booking in queryset:
        if booking.status == 'CONFIRMED':
            try:
                send_booking_confirmed_email(booking)
                success_count += 1
            except Exception as e:
                failure_count += 1
                print(f"Failed to resend email for booking {booking.id}: {e}")
        else:
            modeladmin.message_user(
                request,
                f"Skipped '{booking.customer_name}' - Booking is not CONFIRMED (Status: {booking.status})",
                level='WARNING'
            )

    if success_count > 0:
        modeladmin.message_user(
            request,
            f"✓ Successfully resent confirmation emails for {success_count} booking(s)!",
            level='SUCCESS'
        )
    if failure_count > 0:
        modeladmin.message_user(
            request,
            f"✗ Failed to send {failure_count} email(s). Check console for details.",
            level='ERROR'
        )

class BookingAdmin(admin.ModelAdmin):
    # --- ADD THIS BLOCK INSIDE BookingAdmin ---
    def changelist_view(self, request, extra_context=None):
        # 1. Get active event
        active_event = Event.objects.annotate(
            seat_count=Count('seat')).order_by('-seat_count').first()
        five_minutes_ago = timezone.now() - timedelta(minutes=5)

        if active_event:
            # Calculate total seats and split seat states
            total_seats = Seat.objects.filter(event=active_event).count()

            booked = Seat.objects.filter(
                event=active_event,
                status='BOOKED'
            ).count()

            locked = Seat.objects.filter(
                event=active_event,
                status='LOCKED',
                lock_time__gte=five_minutes_ago
            ).count()
        else:
            total_seats = 0
            booked = 0
            locked = 0

        available = total_seats - booked - locked

        # 2. Create the message
        msg = (
            f"📊 LIVE STATUS: Total Seats: {total_seats}   |   "
            f"🔴 Booked: {booked}   |   ⚫ Locked: {locked}   |   🟢 Available: {available}"
        )

        # 3. Show it at the top of the page (as a persistent notification)
        self.message_user(request, msg, level='WARNING')

        # 4. Load the page as usual
        return super().changelist_view(request, extra_context=extra_context)
    # Added 'quantity' to the list
    list_display = ('customer_name', 'status', 'quantity',
                    'email', 'phone',   'razorpay_payment_id')
    list_filter = ('status',)
    search_fields = ('customer_name', 'email')
    actions = [export_bookings_to_csv, resend_confirmation_emails]

    def save_model(self, request, obj, form, change):
        if change:
            try:
                old_version = Booking.objects.get(pk=obj.pk)
                should_send_email = (old_version.status !=
                                     'CONFIRMED' and obj.status == 'CONFIRMED')

                # Mark seats as BOOKED (confirmed) and clear lock_time
                if should_send_email:
                    from django.utils import timezone
                    obj.seats.all().update(status='BOOKED', lock_time=None)
            except Booking.DoesNotExist:
                should_send_email = False
        else:
            should_send_email = False

        # Save to database first (commit transaction)
        super().save_model(request, obj, form, change)

        # Send email directly (no threading - avoids being killed on PythonAnywhere)
        if should_send_email:
            try:
                from .emails import send_booking_confirmed_email
                send_booking_confirmed_email(obj)
                self.message_user(
                    request, f"✓ Booking confirmed! Email with tickets sent to {obj.email}", level='SUCCESS')
            except Exception as e:
                self.message_user(
                    request, f"✗ Booking confirmed but email failed: {str(e)}", level='ERROR')
                print(f"Email Error: {e}")
                import traceback
                traceback.print_exc()

# --- EVENT ADMIN (NEW: Shows Stats) ---


class EventAdmin(admin.ModelAdmin):
    # Columns to show in the Event list
    list_display = ('name', 'total_capacity_display',
                    'confirmed_booked', 'actual_available')

    # 1. Total Capacity (Hardcoded to 86)
    def total_capacity_display(self, obj):
        return 86
    total_capacity_display.short_description = "Total Seats"

    # 2. CONFIRMED ONLY (Sold)
    def confirmed_booked(self, obj):
        # Counts only bookings where status is 'Confirmed'
        booked = Booking.objects.filter(event=obj, status='CONFIRMED').aggregate(
            Sum('quantity'))['quantity__sum']
        return booked if booked else 0
    confirmed_booked.short_description = "✅ Confirmed Sold"

    # 3. AVAILABLE (Total - Confirmed)
    def actual_available(self, obj):
        confirmed = self.confirmed_booked(obj)
        total = self.total_capacity_display(obj)
        # Simple Math: 86 - Sold
        return total - confirmed
    actual_available.short_description = "🟢 Available"


class WaitlistAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'timestamp')  # Columns to show
    search_fields = ('name', 'phone')              # Search bar capability
    list_filter = ('timestamp',)                   # Filter by date
    ordering = ('-timestamp',)                     # Newest on top


# Register the Event with these new stats
admin.site.register(Waitlist, WaitlistAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Booking, BookingAdmin)
