from django.apps import AppConfig
import threading
import time


class BookingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'booking'

    def ready(self):
        import booking.signals

        # Start background task to release stale locks every 5 minutes
        self.start_background_release_task()

    def start_background_release_task(self):
        """Start a background thread to automatically release stale locks every 5 minutes"""
        # Check if thread is already running to avoid duplicates on reload
        if threading.current_thread().name != 'MainThread':
            return

        thread = threading.Thread(target=self._run_release_task, daemon=True)
        thread.name = 'SeatLockReleaseThread'
        thread.start()

    def _run_release_task(self):
        """Background task that runs every 5 minutes"""
        import time
        from django.utils import timezone
        from datetime import timedelta
        from django.db import connections
        from django.db.models import Q
        from booking.models import Seat, Booking

        # Wait 5 seconds before first run to ensure Django is fully initialized
        time.sleep(5)

        while True:
            try:
                # Release stale locks every 5 minutes
                time.sleep(300)  # 5 minutes in seconds

                cutoff = timezone.now() - timedelta(minutes=5)

                # Get seat IDs that are stale and have no pending booking
                # Use subquery to avoid N+1 queries and long transaction holds
                stale_seat_ids = Seat.objects.filter(
                    status="LOCKED", lock_time__lt=cutoff
                ).exclude(
                    # Exclude if part of pending booking
                    Q(booking__status='PENDING')
                ).distinct().values_list('id', flat=True)

                # Batch update all eligible seats at once (single query)
                if stale_seat_ids:
                    updated_count = Seat.objects.filter(
                        id__in=stale_seat_ids
                    ).update(status="AVAILABLE", lock_time=None)

                    if updated_count > 0:
                        print(
                            f"[Auto-Release] Released {updated_count} abandoned locked seat(s) at {timezone.now()}")

                # Close all database connections to release locks immediately
                connections.close_all()
            except Exception as e:
                print(f"[Auto-Release Error] {e}")
                try:
                    connections.close_all()
                except:
                    pass
                # Continue running even if there's an error
                time.sleep(300)
