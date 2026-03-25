# Seating Chart Booking System Implementation

## Overview
I've implemented a complete seating chart booking system similar to BookMyShow, with the following flow:

### User Flow:
1. User opens seating chart page → sees seat grid with quantity selector
2. User selects "how many seats" (e.g., 3)
3. User clicks on seats → auto-selects up to the required quantity
4. When N seats selected → "Confirm" button activates
5. Click Confirm → Details modal (name, email, phone)
6. Click "Proceed to Pay" → Payment modal (QR code + UPI + UTR input)
7. User scans QR or copies UPI, makes payment, enters UTR
8. Booking submitted (PENDING status) - seats reserved
9. Admin verifies payment in Django admin and clicks "CONFIRMED"
10. User receives email with booking details and seats

## Files Modified/Created:

### 1. **Backend - Views** (`booking/views.py`)
- ✅ `seat_map_page()` - Renders seating chart page with booked seats data
- ✅ `submit_seat_booking()` - Accepts seat booking with UTR (manual payment)
- ✅ `calculate_seat_price()` - Calculates total price based on seat rows

**Updated imports:**
```python
from django.utils import timezone
from datetime import timedelta
from .models import ... Seat
```

### 2. **Frontend - HTML** (`booking/templates/booking/seat_map_pick.html`)
- ✅ Added quantity selector section (top of page)
- ✅ Added payment modal with QR code + UPI + UTR input field
- ✅ Added back button to return to home
- ✅ Integrated checkbox for payment confirmation

**New UI Elements:**
- `.quantity-selector` - Shows "How many seats?" with +/- buttons
- `#payment-modal` - Payment modal with QR code and UTR input
- `.qty-controls` - Quantity adjustment buttons
- `.qty-price` - Real-time price calculation

### 3. **Frontend - JavaScript** (`booking/static/booking/script_seats.js`)
**Created NEW script (not modifying old script.js to preserve FCFS)**

**Key Features:**
- ✅ Auto-select N seats when user clicks (BookMyShow-style)
- ✅ When user clicks beyond N seats, replaces oldest with new selection
- ✅ Real-time price calculation
- ✅ Two-modal flow: Details → Payment
- ✅ UTR input for manual payment verification
- ✅ Copy-to-clipboard UPI ID function
- ✅ Form submission to `/submit-seats/` endpoint

**Global State:**
```javascript
let qtyNeeded = 1;           // How many seats needed
window.selectedSeats = Set() // Currently selected seats
```

### 4. **URLs** (`booking/urls.py`)
Added new route:
```python
path('seats/', views.seat_map_page, name='seat_map'),
path('submit-seats/', views.submit_seat_booking, name='submit_seats'),
```

### 5. **Home Page Button** (`booking/templates/booking/seat_map_general.html`)
Added button on main page:
```html
<button class="btn-main btn-next" onclick="window.location.href='/seats/';">
    📍 Choose Your Seats
</button>
```

## Database Model Integration

The system uses existing models:
- **Seat** - Row/number/status tracking (AVAILABLE, LOCKED, BOOKED)
- **Booking** - Stores customer info + ManyToMany relation with Seats
- **Event** - Event details (pricing by row)

## Admin Workflow

1. **Booking Created** → Status: PENDING (waiting for payment verification)
2. **Customer sees** → Details and payment instructions
3. **Admin Verifies** → In Django admin, change status to CONFIRMED
4. **Automatic Email** → `send_confirmation_email()` sends ticket details

Email includes:
- Confirmation of booking
- Seats booked
- Event details (date, time, venue)

## API Endpoints

### POST `/submit-seats/`
Submits seat booking with payment details

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+919876543210",
  "seats": ["A1", "A2", "A3"],
  "utr": "TXN123456789"
}
```

**Response:**
```json
{
  "success": true,
  "booking_id": 42
}
```

## Key Features

✅ **Auto-selection Logic**
- Select up to N seats by clicking
- If clicking beyond N, replaces oldest selected
- Deselect by clicking already-selected seat

✅ **Price Calculation**
- TOP rows (A-F): ₹300
- BOTTOM rows (G-P): ₹200
- Dynamic total calculation

✅ **Manual Payment Flow**
- QR code scan option
- UPI copy-to-clipboard
- Manual UTR entry for verification
- Admin confirms after checking payment

✅ **Seat Locking**
- Currently: No time-based lock (immediate booking)
- Can be enhanced with 10-minute lock + release

✅ **Email Notifications**
- Trigger on admin "CONFIRMED" status change
- Includes seat numbers and event details

## How to Use

### For Users:
1. Go to `/` (home page)
2. Click "📍 Choose Your Seats" button
3. Select quantity (e.g., 3 seats)
4. Click on 3 available seats
5. Click "Confirm" button
6. Fill details (name, email, phone)
7. Click "Proceed to Pay"
8. Scan QR code or copy UPI ID
9. Enter Transaction ID (UTR)
10. Click "Confirm Booking"
11. Wait for admin verification
12. Receive email with confirmation

### For Admin:
1. Go to Django Admin: `/admin/booking/booking/`
2. Find the PENDING booking
3. Change status to "CONFIRMED"
4. Save
5. Automatic email sent to customer

## Future Enhancements

- [ ] Add 10-minute lock timeout for seats (like BookMyShow)
- [ ] Generate PDF tickets with seat numbers
- [ ] SMS notifications alongside email
- [ ] Payment verification webhook from Razorpay
- [ ] Prevent double-bookings during concurrent requests
- [ ] Seat blocking visualization for admin
- [ ] Analytics dashboard for booking trends

## Testing

To test the system:

1. Create an Event in Django admin
2. Create 86 Seat objects with proper rows (A-P) and numbers (1-13)
3. Go to `/seats/` in browser
4. Select quantity and seats
5. Fill booking form with UTR "TESTPAYMENT123"
6. Submit booking
7. Go to admin and confirm payment
8. Check email for confirmation

## Notes

- Old FCFS script.js is preserved (new script_seats.js used for seating chart)
- Seating chart and FCFS can coexist (users choose which path)
- No Razorpay integration (uses manual UTR verification like FCFS)
- All prices configurable via Event model (top_price, bottom_price)
