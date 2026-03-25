from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_booking_confirmation_email(booking):
    """Send confirmation email when booking is submitted (PENDING status)"""
    try:
        # Get seat details
        seats = booking.seats.all()
        seat_list = [f"{seat.row}{seat.number}" for seat in seats]

        # Email content
        subject = f"Booking Confirmation - {booking.event.name}"

        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.8;">
                <h2>Booking Confirmation</h2>
                <p>Dear {booking.customer_name},</p>
                <p>Your booking has been successfully submitted!</p>
                
                <h3>Booking Details:</h3>
                <p><strong>Event:</strong> {booking.event.name}</p>
                <p><strong>Date:</strong> 26 March 2026, Thursday</p>
                <p><strong>Time:</strong> 6:15 PM to 8:15 PM</p>
                <p><strong>Venue:</strong> MES auditorium, Mayur Colony</p>
                <p><strong>Seats:</strong> {', '.join(seat_list)}</p>
                <p><strong>Quantity:</strong> {booking.quantity}</p>
                <p><strong>Amount:</strong> ₹{booking.amount}</p>
                <p><strong>Transaction ID (UTR):</strong> {booking.razorpay_payment_id}</p>
                <p><strong>Status:</strong> {booking.status} (Awaiting verification)</p>
                
                <h3>Next Steps:</h3>
                <p>Our admin team will verify your payment within 24 hours.</p>
                <p>You will receive a confirmation email once your booking is confirmed.</p>
                
                <p>Thank you for booking with us!</p>
                <hr>
                <p style="color: #666; font-size: 12px;">This is an automated email.</p>
                <p style="color: #666; font-size: 12px;">Please do not reply to this email.</p>
            </body>
        </html>
        """

        send_mail(
            subject,
            # Plain text version
            f"""Booking Confirmation - {booking.event.name}

Dear {booking.customer_name},

Your booking has been successfully submitted!

Booking Details:
Event: {booking.event.name}
Date: 26 March 2026, Thursday
Time: 6:15 PM to 8:15 PM
Venue: MES auditorium, Mayur Colony
Seats: {', '.join(seat_list)}
Quantity: {booking.quantity}
Amount: Rs.{booking.amount}
Transaction ID (UTR): {booking.razorpay_payment_id}
Status: {booking.status} (Awaiting verification)

Next Steps:
Our admin team will verify your payment within 24 hours. You will receive a confirmation email once your booking is confirmed.

Thank you for booking with us!

This is an automated email. Please do not reply to this email.""",
            settings.EMAIL_HOST_USER,
            [booking.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✓ Confirmation email sent to {booking.email}")
    except Exception as e:
        print(f"✗ Failed to send email to {booking.email}: {e}")


def send_booking_confirmed_email(booking):
    """Send confirmation email when admin confirms booking (CONFIRMED status)"""
    try:
        from io import BytesIO
        from django.core.mail import EmailMessage
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from PyPDF2 import PdfReader, PdfWriter
        import os

        seats = booking.seats.all().order_by('row', 'number')
        seat_list = [f"{seat.row}{seat.number}" for seat in seats]

        def seat_price(seat):
            return booking.event.top_price if seat.row in "ABCDEFG" else booking.event.bottom_price

        subject = f"Booking Confirmed - {booking.event.name}"

        html_message = f"""
        <html>
            <body style='font-family: Arial, sans-serif; line-height: 1.8;'>
                <h2>Your Booking is Confirmed!</h2>
                <p>Dear {booking.customer_name},</p>
                <p>Great news!</p>
                <p>Your booking has been confirmed and verified.</p>
                
                <h3>Final Booking Details:</h3>
                <p><strong>Event:</strong> {booking.event.name}</p>
                <p><strong>Date:</strong> 26 March 2026, Thursday</p>
                <p><strong>Time:</strong> 6:15 PM to 8:15 PM</p>
                <p><strong>Venue:</strong> MES auditorium, Mayur Colony</p>
                <p><strong>Seats:</strong> {', '.join(seat_list)}</p>
                <p><strong>Total Amount Paid:</strong> ₹{booking.amount}</p>
                
                <h3>Important:</h3>
                <p>Please keep this email as your booking confirmation.</p>
                <p>You will need it at the venue.</p>
                <p>Your PDF tickets are attached to this email (one per seat).</p>
                
                <hr>
                <p style='color: #666; font-size: 12px;'>This is an automated email.</p>
                <p style='color: #666; font-size: 12px;'>Please do not reply to this email.</p>
            </body>
        </html>
        """

        # Load ticket template PDF and overlay text
        template_path = os.path.join(os.path.dirname(
            __file__), 'templates', 'booking', 'Ticket.pdf')

        def build_ticket_pdf(single_seat_label, single_seat_price):
            overlay_buffer = BytesIO()
            overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=letter)

            overlay_canvas.setFont("Helvetica-Bold", 14)
            overlay_canvas.drawCentredString(110, 162, booking.customer_name)

            overlay_canvas.setFont("Helvetica", 12)
            overlay_canvas.drawCentredString(80, 120, single_seat_label)

            overlay_canvas.setFont("Helvetica", 10)
            overlay_canvas.drawCentredString(
                175, 120, f"Rs.{single_seat_price}")

            overlay_canvas.showPage()
            overlay_canvas.save()
            overlay_buffer.seek(0)

            try:
                with open(template_path, 'rb') as template_file:
                    reader = PdfReader(template_file)
                    overlay_reader = PdfReader(overlay_buffer)
                    writer = PdfWriter()

                    template_page = reader.pages[0]
                    overlay_page = overlay_reader.pages[0]
                    template_page.merge_page(overlay_page)
                    writer.add_page(template_page)

                    final_buffer = BytesIO()
                    writer.write(final_buffer)
                    pdf_bytes = final_buffer.getvalue()
                    final_buffer.close()
            except Exception as e:
                print(f"Warning: Could not load template PDF ({e}), using overlay only")
                pdf_bytes = overlay_buffer.getvalue()

            overlay_buffer.close()
            return pdf_bytes

        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[booking.email],
        )
        email.content_subtype = "html"

        for seat in seats:
            seat_label = f"{seat.row}{seat.number}"
            seat_ticket_pdf = build_ticket_pdf(seat_label, seat_price(seat))
            email.attach(f"ticket_{seat_label}.pdf",
                         seat_ticket_pdf, "application/pdf")

        email.send(fail_silently=False)

        print(
            f"✓ Confirmed booking email with {len(seat_list)} PDF ticket(s) sent to {booking.email}")
    except Exception as e:
        print(f"✗ Failed to send confirmation email to {booking.email}: {e}")
        import traceback
        traceback.print_exc()
