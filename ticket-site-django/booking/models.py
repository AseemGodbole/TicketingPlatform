from django.db import models
from django.utils import timezone
from datetime import timedelta


class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    time = models.TimeField()
    venue = models.CharField(max_length=200)
    top_price = models.PositiveIntegerField(default=350)
    bottom_price = models.PositiveIntegerField(default=250)

    def __str__(self):
        return self.name


class Seat(models.Model):
    STATUS_CHOICES = [
        ("AVAILABLE", "Available"),
        ("LOCKED", "Locked"),
        ("BOOKED", "Booked"),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    row = models.CharField(max_length=2)
    number = models.PositiveIntegerField()
    is_top_block = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="AVAILABLE")
    lock_time = models.DateTimeField(null=True, blank=True)

    def is_stale(self):
        if self.status != "LOCKED" or not self.lock_time:
            return False
        return timezone.now() - self.lock_time > timedelta(minutes=10)

    def __str__(self):
        return f"{self.row}{self.number} ({self.status})"

    class Meta:
        unique_together = ("event", "row", "number")


class Booking(models.Model):
    # Status Choices for Dropdown
    STATUS_OPTIONS = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('FAILED', 'Failed')
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    seats = models.ManyToManyField(Seat, blank=True)

    # NEW: Separate Quantity Field
    quantity = models.PositiveIntegerField(default=1)

    amount = models.PositiveIntegerField()

    # CHANGED: Now uses choices (Dropdown)
    status = models.CharField(
        max_length=20, choices=STATUS_OPTIONS, default="PENDING")

    razorpay_order_id = models.CharField(max_length=128, blank=True, null=True)
    razorpay_payment_id = models.CharField(
        max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} - {self.status}"


class Waitlist(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.phone}"
