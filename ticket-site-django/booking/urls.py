from django.urls import path
from . import views

urlpatterns = [
    # 1. Homepage - Direct to seating chart
    path('', views.seat_map_page, name='index'),

    # 2. The Manual Booking Submission (matches 'def submit_manual_booking')
    path('submit-manual/', views.submit_manual_booking, name='submit_manual'),
    path('submit-waitlist/', views.submit_waitlist, name='submit_waitlist'),

    # 3. Seating Chart Booking
    path('seats/', views.seat_map_page, name='seat_map'),
    path('submit-seats/', views.submit_seat_booking, name='submit_seats'),

    # AJAX endpoint for seat locking
    path('lock-seats/', views.lock_seats, name='lock_seats'),

    # 4. Old FCFS page (if needed)
    path('fcfs/', views.index, name='fcfs'),
]
