from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from booking.models import Seat


class Command(BaseCommand):
    help = "Releases seats locked for more than 5 minutes"

    def handle(self, *args, **kwargs):
        cutoff = timezone.now() - timedelta(minutes=5)
        stale_seats = Seat.objects.filter(
            status="LOCKED", lock_time__lt=cutoff)
        count = stale_seats.count()
        stale_seats.update(status="AVAILABLE", lock_time=None)
        self.stdout.write(self.style.SUCCESS(
            f"Released {count} stale locked seats."))
