from django.contrib import admin
from .models import Event, Seat


@admin.action(description="Mark selected seats as BOOKED")
def mark_as_booked(modeladmin, request, queryset):
    queryset.update(status="BOOKED")


@admin.action(description="Mark selected seats as AVAILABLE")
def mark_as_available(modeladmin, request, queryset):
    queryset.update(status="AVAILABLE")


class SeatAdmin(admin.ModelAdmin):
    list_display = ("event", "row", "number", "status", "is_top_block")
    list_filter = ("event", "row", "status", "is_top_block")
    search_fields = ("row", "number")
    actions = [mark_as_booked, mark_as_available]


admin.site.register(Event)
admin.site.register(Seat, SeatAdmin)
