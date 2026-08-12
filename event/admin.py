from django.contrib import admin
from .models import Category, Event, Member, Contact, Message, Venue, Sponsor, Resource, ResourceAllocation, Ticket, Attendance, Vendor, Contract, Budget, Expense, Announcement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'priority', 'status', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('priority', 'status')

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'location', 'created_at')
    search_fields = ('name', 'location')

@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'created_at')
    search_fields = ('name',)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'venue', 'start_date', 'status')
    search_fields = ('name', 'venue__name')
    list_filter = ('category', 'status')

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'event', 'role', 'status')
    search_fields = ('name', 'email')
    list_filter = ('role', 'status')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'submitted_at')
    search_fields = ('name', 'email', 'subject')
    readonly_fields = ('submitted_at',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'event', 'created_at', 'is_read')
    search_fields = ('sender__username', 'recipient__username', 'content')
    list_filter = ('event', 'created_at', 'is_read')

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'resource_type', 'total_quantity', 'created_at')
    search_fields = ('name',)
    list_filter = ('resource_type',)

@admin.register(ResourceAllocation)
class ResourceAllocationAdmin(admin.ModelAdmin):
    list_display = ('event', 'resource', 'allocated_quantity', 'allocated_at')
    search_fields = ('event__name', 'resource__name')
    list_filter = ('resource__resource_type',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'member', 'event', 'status', 'issue_date')
    search_fields = ('ticket_number', 'member__name', 'uuid')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('member', 'event', 'check_in_time', 'status', 'verified_by')
    search_fields = ('member__name', 'event__name')
    list_filter = ('status',)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_category', 'contact_person', 'email', 'rating')
    search_fields = ('name', 'service_category')


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'event', 'contract_amount', 'status')
    search_fields = ('vendor__name', 'event__name')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('event', 'total_amount', 'created_at')
    search_fields = ('event__name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'budget', 'amount', 'category', 'approved')
    search_fields = ('name', 'budget__event__name')
    list_filter = ('category', 'approved')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'audience', 'created_at', 'is_active')
    search_fields = ('title', 'content')
    list_filter = ('audience', 'is_active', 'created_at')

