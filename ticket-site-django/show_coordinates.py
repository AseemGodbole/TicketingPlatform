"""
Debug utility to show coordinate grid on ticket template PDF.
Run this to see where coordinates are on your ticket.
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import os

# Path to your ticket template
template_path = r'c:\Users\aseem\OneDrive\Desktop\ticket-site-django\booking\templates\booking\Ticket.pdf'
output_path = r'c:\Users\aseem\OneDrive\Desktop\ticket-site-django\ticket_with_coordinates.pdf'

# Create overlay with coordinate grid
overlay_buffer = BytesIO()
c = canvas.Canvas(overlay_buffer, pagesize=letter)
width, height = letter

# Draw grid lines every 50 points
c.setStrokeColorRGB(0.9, 0.9, 0.9)  # Light gray
for x in range(0, int(width), 50):
    c.line(x, 0, x, height)
for y in range(0, int(height), 50):
    c.line(0, y, width, y)

# Draw coordinate labels every 50 points
c.setFillColorRGB(1, 0, 0)  # Red text
c.setFont("Helvetica", 8)
for x in range(0, int(width), 50):
    for y in range(0, int(height), 50):
        c.drawString(x + 2, y + 2, f"({x},{y})")

# Draw major axis lines
c.setStrokeColorRGB(0, 0, 1)  # Blue
c.setLineWidth(2)
c.line(0, height/2, width, height/2)  # Horizontal center
c.line(width/2, 0, width/2, height)   # Vertical center

# Add instructions
c.setFillColorRGB(0, 0, 0)
c.setFont("Helvetica-Bold", 10)
c.drawString(50, height - 30,
             "COORDINATE GRID - Red numbers show (x, y) positions")
c.drawString(50, height - 45,
             "Blue lines = center axes | Gray grid = 50-point spacing")

c.showPage()
c.save()
overlay_buffer.seek(0)

# Merge with template
try:
    with open(template_path, 'rb') as template_file:
        reader = PdfReader(template_file)
        overlay_reader = PdfReader(overlay_buffer)
        writer = PdfWriter()

        template_page = reader.pages[0]
        overlay_page = overlay_reader.pages[0]

        template_page.merge_page(overlay_page)
        writer.add_page(template_page)

        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

    print(f"✓ Success! Open this file to see coordinates:")
    print(f"  {output_path}")
    print()
    print("How to use:")
    print("1. Open the PDF and find your white boxes")
    print("2. Note the (x, y) coordinates shown in red")
    print("3. Tell me the coordinates for name, seat, and price boxes")

except Exception as e:
    print(f"✗ Error: {e}")
    print(f"Make sure the template exists at: {template_path}")

overlay_buffer.close()
