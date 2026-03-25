"""
Preview ticket with test data
"""
import os
import django
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticketsite.settings')
django.setup()

# Template path
template_path = os.path.join(os.path.dirname(
    __file__), 'booking', 'templates', 'booking', 'Ticket.pdf')

# Test data
name = "Aseem Godbole"
seats = "H18"
price = 200

# Create overlay with text
overlay_buffer = BytesIO()
overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=letter)

# Place text at coordinates
# Name box
overlay_canvas.setFont("Helvetica-Bold", 14)
overlay_canvas.drawCentredString(110, 162, name)

# Seat number box
overlay_canvas.setFont("Helvetica", 12)
overlay_canvas.drawCentredString(80, 120, seats)

# Price box
overlay_canvas.setFont("Helvetica", 10)
overlay_canvas.drawCentredString(175, 120, f"Rs.{price}")

overlay_canvas.showPage()
overlay_canvas.save()
overlay_buffer.seek(0)

# Merge overlay with template
try:
    with open(template_path, 'rb') as template_file:
        reader = PdfReader(template_file)
        overlay_reader = PdfReader(overlay_buffer)
        writer = PdfWriter()

        # Get first page from template
        template_page = reader.pages[0]
        overlay_page = overlay_reader.pages[0]

        # Merge overlay onto template
        template_page.merge_page(overlay_page)
        writer.add_page(template_page)

        # Save final PDF
        output_path = os.path.join(os.path.dirname(
            __file__), 'preview_ticket_output.pdf')
        with open(output_path, 'wb') as f:
            writer.write(f)

        print(f"✓ Preview ticket generated!")
        print(f"  Name: {name}")
        print(f"  Seat: {seats}")
        print(f"  Price: Rs.{price}")
        print(f"  Saved to: {output_path}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

overlay_buffer.close()
