from booking.models import Event, Seat
from django.utils import timezone
from datetime import date, time
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticketsite.settings')
django.setup()


# Create an event if it doesn't exist
event, created = Event.objects.get_or_create(
    name="Geet Ramayan",
    defaults={
        'date': date.today(),
        'time': time(19, 30),
        'venue': 'The Box Too, Pune',
        'top_price': 350,
        'bottom_price': 250
    }
)

print(f"Event: {event.name} ({'created' if created else 'exists'})")

# Define seat counts per row based on ROW_SHAPE from script.js
# Format: row: total_seats
ROW_SEATS = {
    'A': 18,
    'B': 4 + 13 + 4,    # 21
    'C': 22,
    'D': 6 + 13 + 6,    # 25
    'E': 7 + 13 + 6,    # 26
    'F': 7 + 13 + 7,    # 27
    'G': 25,
    'H': 7 + 13 + 7,    # 27
    'I': 26,
    'J': 7 + 13 + 7,    # 27
    'K': 26,
    'L': 7 + 13 + 7,    # 27
    'M': 24,
    'N': 5 + 13 + 6,    # 24
    'O': 18,
    'P': 7 + 10 + 7,    # 24
}

total_created = 0

# First, delete old seats for this event
Seat.objects.filter(event=event).delete()

for row, max_seats in ROW_SEATS.items():
    for num in range(1, max_seats + 1):
        seat, created = Seat.objects.get_or_create(
            event=event,
            row=row,
            number=num,
            defaults={'status': 'AVAILABLE', 'is_top_block': row in [
                'A', 'B', 'C', 'D', 'E', 'F']}
        )
        if created:
            total_created += 1

total_seats = sum(ROW_SEATS.values())
print(f"✓ Created {total_created} seats")
print(
    f"✓ Total seats: {Seat.objects.filter(event=event).count()} (expected: {total_seats})")
print("✓ Data setup complete!")
