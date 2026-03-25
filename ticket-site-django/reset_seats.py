from booking.models import Seat
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticketsite.settings')
django.setup()


count = Seat.objects.all().update(status='AVAILABLE', lock_time=None)
print(f'✓ Reset {count} seats to AVAILABLE')
