from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Booking


# --- Release seats when booking is deleted ---
@receiver(pre_delete, sender=Booking)
def release_seats_on_booking_delete(sender, instance, **kwargs):
    """
    Release seats when a booking is deleted from admin.
    Uses pre_delete so we can access the ManyToMany relationship before it's cleared.
    """
    seats_to_release = list(instance.seats.all())  # Get seats before deletion
    for seat in seats_to_release:
        seat.status = 'AVAILABLE'
        seat.lock_time = None
        seat.save()

    print(
        f"✓ Released {len(seats_to_release)} seats from deleted booking #{instance.id}")
