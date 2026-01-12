from django.db import models
from django.utils import timezone
from datetime import timedelta


class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    time = models.TimeField()
    venue = models.CharField(max_length=200)
    top_price = models.PositiveIntegerField(default=300)
    bottom_price = models.PositiveIntegerField(default=200)


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
    lock_time = models.DateTimeField(null=True, blank=True)   # 🔥 Add this

    def is_stale(self):
        """Returns True if seat is locked but timeout passed."""
        if self.status != "LOCKED":
            return False
        if not self.lock_time:
            return False

        return timezone.now() - self.lock_time > timedelta(minutes=10)
        # 🔥 10 mins lock window (change if you want)

    def __str__(self):
        return f"{self.row}{self.number} ({self.status})"

    class Meta:
        unique_together = ("event", "row", "number")


class Booking(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    seats = models.ManyToManyField(Seat)
    amount = models.PositiveIntegerField()  # rupees
    status = models.CharField(max_length=10, choices=[(
        "PENDING", "Pending"), ("SUCCESS", "Success"), ("FAILED", "Failed")], default="PENDING")
    razorpay_order_id = models.CharField(max_length=128, blank=True, null=True)
    razorpay_payment_id = models.CharField(
        max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
