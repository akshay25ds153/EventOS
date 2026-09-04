from django.http import JsonResponse
from django.views.decorators.http import require_POST
from openai import OpenAI, AuthenticationError, RateLimitError
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.db import transaction
from datetime import date
from django.core.exceptions import PermissionDenied
from django.conf import settings

from .models import Category, Event, Member, Contact, Message, Venue, Sponsor, Resource, ResourceAllocation, Vendor, Contract, Ticket, Budget, Expense, Attendance, Announcement
from .forms import CategoryForm, EventForm, MemberForm, ContactForm, UserSignupForm, SelfRegistrationForm, VenueForm, SponsorForm, ResourceForm, ResourceAllocationForm, VendorForm, ContractForm, BudgetForm, ExpenseForm, AnnouncementForm
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .utils import generate_ticket_qr, generate_ticket_pdf, generate_pdf_report
import csv
import logging

logger = logging.getLogger('event')

# ==========================================================================
# REPORTING & EXPORT MODULE HELPERS
# ==========================================================================

def check_export_permission(request):
    """
    Checks if the current user has permissions to run exports (staff or admin/organizer profile).
    Raises PermissionDenied if not authorized.
    """
    if request.user.is_staff:
        return True
    profile = getattr(request.user, 'profile', None)
    if profile and profile.role in ['admin', 'organizer']:
        return True
    raise PermissionDenied("Access Denied: Only administrators and organizers can export data.")

def write_csv_with_bom(response, headers, rows):
    """
    Writes a CSV spreadsheet including the UTF-8 BOM character for Excel compatibility.
    """
    response.write('\ufeff'.encode('utf-8'))
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

# ==========================================================================
# PUBLIC PAGES
# ==========================================================================


def landing_page(request):
    return render(request, 'home/index.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Contact Message Sent Successfully")
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact/contact.html', {'form': form})

# ==========================================================================
# AUTHENTICATION
# ==========================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user_model = get_user_model()

        user = authenticate(request=request, username=identifier, password=password)

        if user is None and '@' in identifier:
            try:
                user_obj = user_model.objects.get(email__iexact=identifier)
            except user_model.DoesNotExist:
                user_obj = None
            except user_model.MultipleObjectsReturned:
                logger.warning("Duplicate email detected during login attempt: %s", identifier)
                messages.error(request, "Multiple accounts are registered with this email address. Please log in using your unique username instead.")
                return render(request, 'authentication/login.html', {'form': form})

            if user_obj is not None:
                user = user_obj
                if not user.check_password(password):
                    user = None

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {identifier}!")
            return redirect('dashboard')

        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'authentication/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('landing')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Registration successful! Welcome to EventOS, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Registration failed. Please correct the error(s) below.")
    else:
        form = UserSignupForm()

    return render(request, 'authentication/register.html', {'form': form})

# ==========================================================================
# DASHBOARD & PROFILE
# ==========================================================================

@login_required
def dashboard_view(request):
    user_role = getattr(getattr(request.user, 'profile', None), 'role', 'viewer')
    total_categories = Category.objects.count()
    total_events = Event.objects.count()
    total_members = Member.objects.count()
    completed_events_count = Event.objects.filter(status='Completed').count()
    
    # Query latest objects
    latest_categories = Category.objects.all().order_by('-created_at')[:3]
    latest_events = Event.objects.all().order_by('-created_at')[:3]
    
    # Upcoming active events
    upcoming_events = Event.objects.filter(
        status='Active',
        start_date__gte=date.today()
    ).order_by('start_date')[:3]

    # Category distribution for Chart 1
    categories_data = Category.objects.annotate(event_count=Count('events'))
    chart_labels = [c.name for c in categories_data]
    chart_data = [c.event_count for c in categories_data]

    # Event status counts for Chart 2
    event_status_labels = ['Active', 'Completed', 'Pending']
    event_status_data = [
        Event.objects.filter(status='Active').count(),
        completed_events_count,
        Event.objects.filter(status='Pending').count()
    ]
    
    context = {
        'total_categories': total_categories,
        'total_events': total_events,
        'total_members': total_members,
        'completed_events_count': completed_events_count,
        'latest_categories': latest_categories,
        'latest_events': latest_events,
        'upcoming_events': upcoming_events,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'event_status_labels': event_status_labels,
        'event_status_data': event_status_data,
        'can_manage_events': request.user.is_authenticated,
        'can_manage_announcements': request.user.is_staff or user_role in ['admin', 'organizer'],
        'can_access_qr_scanner': request.user.is_staff or user_role in ['admin', 'organizer'] or Event.objects.filter(organizers=request.user).exists(),
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
def profile_view(request):
    user = request.user
    user_profile, _ = user.profile.__class__.objects.get_or_create(user=user) if hasattr(user, 'profile') else (None, False)
    # Ensure profile exists
    from event.models import UserProfile
    user_profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        # Handle Profile Update
        if 'edit_profile' in request.POST:
            user.first_name = request.POST.get('first_name', user.first_name).strip()
            user.last_name = request.POST.get('last_name', user.last_name).strip()
            user.email = request.POST.get('email', user.email).strip()
            user.save()
            # Handle profile photo
            if 'profile_photo' in request.FILES:
                user_profile.profile_photo = request.FILES['profile_photo']
            user_profile.phone = request.POST.get('phone', user_profile.phone).strip()
            user_profile.bio = request.POST.get('bio', user_profile.bio).strip()
            
            # Save style preferences
            user_profile.theme_preference = request.POST.get('theme_preference', user_profile.theme_preference)
            user_profile.accent_color = request.POST.get('accent_color', user_profile.accent_color)
            user_profile.font = request.POST.get('font', user_profile.font)
            user_profile.border_radius = request.POST.get('border_radius', user_profile.border_radius)
            user_profile.compact_mode = 'compact_mode' in request.POST
            user_profile.animations_enabled = 'animations_enabled' in request.POST
            user_profile.reduced_motion = 'reduced_motion' in request.POST
            
            # Save settings / localization
            user_profile.timezone = request.POST.get('timezone', user_profile.timezone).strip()
            user_profile.language = request.POST.get('language', user_profile.language).strip()
            user_profile.notifications_enabled = 'notifications_enabled' in request.POST
            
            user_profile.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')

        # Handle Password Change
        elif 'change_password' in request.POST:
            pass_form = PasswordChangeForm(user, request.POST)
            if pass_form.is_valid():
                pass_form.save()
                messages.success(request, "Password changed successfully.")
                return redirect('profile')
            else:
                messages.error(request, "Error changing password. Please make sure data matches.")
                return render(request, 'authentication/profile.html', {
                    'pass_form': pass_form,
                    'user_profile': user_profile,
                })

    pass_form = PasswordChangeForm(user)
    return render(request, 'authentication/profile.html', {
        'pass_form': pass_form,
        'user_profile': user_profile,
    })

# ==========================================================================
# CATEGORY CRUD
# ==========================================================================

@login_required
def category_list(request):
    categories = Category.objects.filter(is_active=True).order_by('-created_at')
    
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"categories_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Category Name', 'Description', 'Active Events Count']
        
        rows = []
        for cat in categories:
            active_events = cat.events.filter(is_active=True).count()
            rows.append([
                cat.name,
                cat.description or 'No Description',
                active_events
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Event Categories Report",
                headers=headers,
                data=rows,
                col_widths=[150, 300, 90],
                landscape_mode=True,
                user=request.user.username,
                total_records=len(categories)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
            
    return render(request, 'category/category-list.html', {
        'categories': categories,
        'can_export_options': request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'role', '') in ['admin', 'organizer'],
    })

@login_required
def create_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Category Created Successfully")
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'category/create-category.html', {'form': form})

@login_required
def category_details(request, pk):
    category = get_object_or_404(Category, pk=pk)
    associated_events = category.events.all()
    return render(request, 'category/category-details.html', {
        'category': category,
        'associated_events': associated_events
    })

@login_required
def edit_category(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can edit categories.")
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category Updated Successfully")
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'category/edit-category.html', {'form': form, 'category': category})

@login_required
def delete_category(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete categories.")
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, "Category Archived Successfully")
        return redirect('category_list')
    return render(request, 'category/delete-category.html', {'category': category})


# ==========================================================================
# ANNOUNCEMENT CRUD
# ==========================================================================

@login_required
def announcement_list(request):
    role = getattr(request.user, 'profile', None).role if hasattr(request.user, 'profile') else 'viewer'
    is_manager = request.user.is_staff or role in ['admin', 'organizer']

    if is_manager:
        announcements = Announcement.objects.all().order_by('-created_at')
    else:
        user_registered_event_ids = Member.objects.filter(user=request.user, is_active=True).values_list('event_id', flat=True)
        user_organized_event_ids = request.user.organized_events.filter(is_active=True).values_list('id', flat=True)
        user_event_ids = list(set(list(user_registered_event_ids) + list(user_organized_event_ids)))

        announcements = Announcement.objects.filter(is_active=True).filter(
            Q(event__isnull=True) | Q(event_id__in=user_event_ids)
        ).filter(
            Q(audience='all') |
            Q(audience=role) |
            (Q(audience='organizer') if role in ['admin', 'organizer'] else Q(pk__in=[])) |
            (Q(audience='volunteer') if role == 'volunteer' else Q(pk__in=[])) |
            (Q(audience='participant') if role == 'viewer' else Q(pk__in=[]))
        ).order_by('-created_at')

    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        filename_base = f"announcements_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Title', 'Content', 'Event', 'Audience', 'Created At']
        rows = []
        for ann in announcements:
            rows.append([
                ann.title,
                ann.content,
                ann.event.name if ann.event else 'Global',
                ann.get_audience_display(),
                ann.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="System Announcements Report",
                headers=headers,
                data=rows,
                col_widths=[100, 200, 80, 80, 80],
                landscape_mode=True,
                user=request.user.username,
                total_records=len(announcements)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response

    return render(request, 'announcement/announcement_list.html', {
        'announcements': announcements,
        'is_manager': is_manager
    })


@login_required
def announcement_details(request, pk):
    role = getattr(request.user, 'profile', None).role if hasattr(request.user, 'profile') else 'viewer'
    is_manager = request.user.is_staff or role in ['admin', 'organizer']
    
    announcement = get_object_or_404(Announcement, pk=pk)
    
    if not is_manager:
        if not announcement.is_active:
            raise PermissionDenied("This announcement is archived.")
        if announcement.event:
            is_member = Member.objects.filter(user=request.user, event=announcement.event, is_active=True).exists()
            is_org = announcement.event.organizers.filter(pk=request.user.pk).exists()
            if not (is_member or is_org):
                raise PermissionDenied("You do not have permission to view this announcement.")
        if announcement.audience != 'all' and announcement.audience != role:
            if not (announcement.audience == 'organizer' and role in ['admin', 'organizer']):
                raise PermissionDenied("This announcement is not targeted to your role.")

    return render(request, 'announcement/announcement_details.html', {
        'announcement': announcement,
        'is_manager': is_manager
    })


@login_required
def create_announcement(request):
    role = getattr(request.user, 'profile', None).role if hasattr(request.user, 'profile') else 'viewer'
    is_manager = request.user.is_staff or role in ['admin', 'organizer']
    if not is_manager:
        raise PermissionDenied("Only staff members and event coordinators can post announcements.")

    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            messages.success(request, "Announcement published successfully.")
            return redirect('announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'announcement/create_announcement.html', {'form': form})


@login_required
def edit_announcement(request, pk):
    role = getattr(request.user, 'profile', None).role if hasattr(request.user, 'profile') else 'viewer'
    is_manager = request.user.is_staff or role in ['admin', 'organizer']
    if not is_manager:
        raise PermissionDenied("Only managers can edit announcements.")

    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.updated_by = request.user
            announcement.save()
            messages.success(request, "Announcement updated successfully.")
            return redirect('announcement_list')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'announcement/edit_announcement.html', {
        'form': form,
        'announcement': announcement
    })


@login_required
def delete_announcement(request, pk):
    role = getattr(request.user, 'profile', None).role if hasattr(request.user, 'profile') else 'viewer'
    is_manager = request.user.is_staff or role in ['admin', 'organizer']
    if not is_manager:
        raise PermissionDenied("Only managers can delete announcements.")

    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        announcement.is_active = False
        announcement.save()
        messages.success(request, "Announcement archived successfully.")
        return redirect('announcement_list')
    return render(request, 'announcement/delete_announcement.html', {'announcement': announcement})


@login_required
def unarchive_announcement(request, pk):
    role = getattr(request.user, 'profile', None).role if hasattr(request.user, 'profile') else 'viewer'
    is_manager = request.user.is_staff or role in ['admin', 'organizer']
    if not is_manager:
        raise PermissionDenied("Only managers can restore announcements.")

    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        announcement.is_active = True
        announcement.save()
        messages.success(request, "Announcement restored successfully.")
        return redirect('announcement_details', pk=announcement.id)
    return redirect('announcement_list')



# ==========================================================================
# EVENT CRUD
# ==========================================================================

def can_manage_event(user, event):
    if user.is_staff:
        return True
    if getattr(user, 'profile', None) and user.profile.role == 'admin':
        return True
    if event and event.organizers.filter(pk=user.pk).exists():
        return True
    return False

@login_required
def event_list(request):
    # Support filter query parameters
    events = Event.objects.filter(is_active=True).select_related('category', 'venue').prefetch_related('organizers', 'members').order_by('-created_at')
    
    # Hide private events unless staff, organizer, or registered attendee
    user = request.user
    filtered_events = []
    for event in events:
        if event.visibility == Event.Visibility.PRIVATE:
            is_authorized = (
                user.is_staff or
                getattr(user, 'profile', None) and user.profile.role == 'admin' or
                event.organizers.filter(pk=user.pk).exists() or
                event.members.filter(user=user).exists()
            )
            if not is_authorized:
                continue
        filtered_events.append(event)
        
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"events_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Event Name', 'Category', 'Venue', 'Start Date', 'End Date', 'Status', 'Capacity', 'Registered']
        
        rows = []
        for event in filtered_events:
            # Python-side filtering to leverage prefetched members without DB queries
            active_count = sum(1 for m in event.members.all() if m.status == 'Active')
            rows.append([
                event.name,
                event.category.name,
                event.venue.name if event.venue else "TBD",
                event.start_date.strftime('%Y-%m-%d'),
                event.end_date.strftime('%Y-%m-%d'),
                event.status,
                event.max_participants,
                active_count
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Events Schedule Report",
                headers=headers,
                data=rows,
                col_widths=[160, 80, 80, 80, 80, 60, 60, 60],
                landscape_mode=True,
                user=request.user.username,
                total_records=len(filtered_events)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
        
    return render(request, 'event/event-list.html', {
        'events': filtered_events,
        'can_manage_events': request.user.is_authenticated,
        'can_export_events': request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'role', '') in ['admin', 'organizer'],
    })

@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            if request.user.is_authenticated:
                event.created_by = request.user
            event.save()
            form.save_m2m()
            messages.success(request, "Event Created Successfully")
            return redirect('event_list')
    else:
        form = EventForm()
    return render(request, 'event/create-event.html', {'form': form})

@login_required
def event_details(request, pk):
    event = get_object_or_404(Event, pk=pk)
    user = request.user
    
    # Visibility authorization check
    if event.visibility == Event.Visibility.PRIVATE:
        is_authorized = (
            user.is_staff or
            getattr(user, 'profile', None) and user.profile.role == 'admin' or
            event.organizers.filter(pk=user.pk).exists() or
            event.members.filter(user=user).exists()
        )
        if not is_authorized:
            raise PermissionDenied("This event is private and you are not authorized to view it.")
            
    # Check if the user is registered
    is_registered = Member.objects.filter(event=event, user=user).exists()
    if not is_registered and user.email:
        is_registered = Member.objects.filter(event=event, email__iexact=user.email).exists()
        
    # Capacity utilization stats
    registered_members = event.members.all()
    registered_count = registered_members.count()
    capacity_utilization = 0
    if event.max_participants > 0:
        capacity_utilization = int((registered_count / event.max_participants) * 100)
    remaining_seats = max(0, event.max_participants - registered_count)
    
    # Duration calculate
    duration_days = (event.end_date - event.start_date).days
    
    # Timeline generation
    timeline_nodes = [
        {'title': 'Created', 'completed': True, 'desc': 'Event logged in repository'},
    ]
    today = date.today()
    if today >= event.registration_deadline:
        timeline_nodes.append({'title': 'Registration Closed', 'completed': True, 'desc': 'No longer accepting new submissions'})
    else:
        timeline_nodes.append({'title': 'Registration Open', 'completed': True, 'desc': f"Deadline: {event.registration_deadline.strftime('%d %b, %Y')}"})
        
    if event.status == Event.EventStatus.ACTIVE:
        timeline_nodes.append({'title': 'Running', 'completed': True, 'desc': 'Event is currently active'})
    elif event.status == Event.EventStatus.COMPLETED:
        timeline_nodes.append({'title': 'Running', 'completed': True, 'desc': 'Event commenced'})
        timeline_nodes.append({'title': 'Completed', 'completed': True, 'desc': 'Event successfully completed'})
    elif event.status == Event.EventStatus.CANCELLED:
        timeline_nodes.append({'title': 'Cancelled', 'completed': True, 'desc': 'Event cancelled'})
    else:
        timeline_nodes.append({'title': 'Pending Schedule', 'completed': False, 'desc': 'Awaiting operational activation'})

    # Similar Events Scoring
    similar_events_scored = []
    other_events = Event.objects.filter(is_active=True, visibility=Event.Visibility.PUBLIC).exclude(pk=event.pk)
    event_org_ids = set(event.organizers.values_list('id', flat=True))
    
    for other in other_events:
        score = 0
        if other.category == event.category:
            score += 3
        if other.venue == event.venue:
            score += 2
        other_org_ids = set(other.organizers.values_list('id', flat=True))
        if event_org_ids & other_org_ids:
            score += 1
        if score > 0:
            similar_events_scored.append((other, score))
            
    similar_events_scored.sort(key=lambda x: x[1], reverse=True)
    similar_events = [item[0] for item in similar_events_scored[:3]]

    # Media and files queries
    gallery_images = event.gallery_images.all()
    attachments = event.attachments.all()
    
    # Permission context flag
    user_can_edit = can_manage_event(user, event)

    return render(request, 'event/event-details.html', {
        'event': event,
        'registered_members': registered_members,
        'registered_count': registered_count,
        'is_registered': is_registered,
        'capacity_utilization': capacity_utilization,
        'remaining_seats': remaining_seats,
        'duration_days': duration_days,
        'timeline_nodes': timeline_nodes,
        'similar_events': similar_events,
        'gallery_images': gallery_images,
        'attachments': attachments,
        'user_can_edit': user_can_edit,
    })

@login_required
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        raise PermissionDenied("You do not have permission to edit this event.")
        
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            evt = form.save(commit=False)
            evt.updated_by = request.user
            evt.save()
            form.save_m2m()
            messages.success(request, "Event Updated Successfully")
            return redirect('event_list')
    else:
        form = EventForm(instance=event)
    return render(request, 'event/edit-event.html', {'form': form, 'event': event})

@login_required
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, event):
        raise PermissionDenied("You do not have permission to delete this event.")
        
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event Deleted Successfully")
        return redirect('event_list')
    return render(request, 'event/delete-event.html', {'event': event})

@login_required
def duplicate_event(request, pk):
    original_event = get_object_or_404(Event, pk=pk)
    if not can_manage_event(request.user, original_event):
        raise PermissionDenied("You do not have permission to duplicate this event.")
        
    duplicated = Event.objects.create(
        name=f"Copy of {original_event.name}",
        category=original_event.category,
        venue=original_event.venue,
        start_date=original_event.start_date,
        end_date=original_event.end_date,
        start_time=original_event.start_time,
        end_time=original_event.end_time,
        max_participants=original_event.max_participants,
        registration_deadline=original_event.registration_deadline,
        banner=original_event.banner,
        description=original_event.description,
        full_description=original_event.full_description,
        operational_requirements=original_event.operational_requirements,
        status=Event.EventStatus.PENDING,
        visibility=original_event.visibility,
        waiting_list_enabled=original_event.waiting_list_enabled,
        created_by=request.user
    )
    duplicated.sponsors.set(original_event.sponsors.all())
    duplicated.organizers.set(original_event.organizers.all())
    
    messages.success(request, "Event duplicated successfully! Edit details below.")
    return redirect('edit_event', pk=duplicated.pk)

@login_required
def event_calendar(request):
    categories = Category.objects.filter(is_active=True)
    venues = Venue.objects.filter(is_active=True)
    return render(request, 'event/event-calendar.html', {
        'categories': categories,
        'venues': venues
    })

@login_required
def events_calendar_api(request):
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    category_id = request.GET.get('category_id')
    venue_id = request.GET.get('venue_id')
    status = request.GET.get('status')
    q = request.GET.get('q')

    events = Event.objects.filter(is_active=True)

    if start_str:
        events = events.filter(end_date__gte=start_str.split('T')[0])
    if end_str:
        events = events.filter(start_date__lte=end_str.split('T')[0])

    if category_id:
        events = events.filter(category_id=category_id)
    if venue_id:
        events = events.filter(venue_id=venue_id)
    if status:
        events = events.filter(status=status)
    if q:
        events = events.filter(Q(name__icontains=q) | Q(description__icontains=q))

    user = request.user
    serialized_events = []

    for event in events:
        if event.visibility == Event.Visibility.PRIVATE:
            is_authorized = (
                user.is_staff or
                getattr(user, 'profile', None) and user.profile.role == 'admin' or
                event.organizers.filter(pk=user.pk).exists() or
                event.members.filter(user=user).exists()
            )
            if not is_authorized:
                continue

        color = '#2563EB'
        if event.category.code == 'CAT-TECH':
            color = '#4F46E5'
        elif event.category.code == 'CAT-CULT':
            color = '#EC4899'
        elif event.category.code == 'CAT-SPRT':
            color = '#10B981'

        if event.status == Event.EventStatus.CANCELLED:
            color = '#EF4444'
        elif event.status == Event.EventStatus.COMPLETED:
            color = '#6B7280'

        from django.urls import reverse
        event_url = reverse('event_details', args=[event.pk])

        serialized_events.append({
            'id': event.id,
            'title': event.name,
            'start': f"{event.start_date}T{event.start_time}",
            'end': f"{event.end_date}T{event.end_time}",
            'url': event_url,
            'color': color,
            'description': event.description,
            'venue_name': event.venue.name if event.venue else "TBD",
            'category_name': event.category.name,
            'status': event.status
        })

    return JsonResponse(serialized_events, safe=False)

def promote_waiting_list(event):
    import uuid
    with transaction.atomic():
        current_active = Member.objects.filter(event=event, status='Active').count()
        if current_active < event.max_participants:
            # Find the oldest pending member
            next_member = Member.objects.filter(event=event, status='Pending').order_by('registration_date').first()
            if next_member:
                next_member.status = 'Active'
                if not next_member.registration_number:
                    next_member.registration_number = f"REG-{event.id}-{next_member.id}"
                next_member.save(update_fields=['status', 'registration_number'])
                
                # Generate Ticket for the newly promoted member
                ticket, created = Ticket.objects.get_or_create(
                    member=next_member,
                    event=event,
                    defaults={
                        'ticket_number': f"TKT-{next_member.id}-{str(uuid.uuid4())[:8].upper()}",
                        'status': Ticket.TicketStatus.ACTIVE
                    }
                )
                if created or not ticket.qr_code or not ticket.pdf_file:
                    generate_ticket_qr(ticket)
                    generate_ticket_pdf(ticket)
                    ticket.save()
            else:
                next_member = None
        else:
            next_member = None

    if next_member:
        # Send email notifications/delayed task
        from .tasks import send_registration_email
        try:
            send_registration_email.delay(next_member.id)
        except Exception:
            pass
        
        # Recurse in case there are more spots
        promote_waiting_list(event)

@login_required
def event_self_register(request, pk):
    import uuid
    event = get_object_or_404(Event, pk=pk)
    
    if event.registration_deadline < date.today():
        messages.error(request, "Registration deadline has passed for this event.")
        return redirect('event_details', pk=pk)
        
    if event.status in ['Completed', 'Cancelled']:
        messages.error(request, f"This event is {event.status.lower()} and no longer accepting registrations.")
        return redirect('event_details', pk=pk)

    is_registered = Member.objects.filter(event=event, user=request.user).exists()
    if not is_registered and request.user.email:
        is_registered = Member.objects.filter(event=event, email__iexact=request.user.email).exists()

    if is_registered:
        messages.warning(request, "You are already registered for this event.")
        return redirect('event_details', pk=pk)

    current_participants = Member.objects.filter(event=event, status='Active').count()
    is_waitlist = False
    if current_participants >= event.max_participants:
        if event.waiting_list_enabled:
            is_waitlist = True
        else:
            messages.error(request, "Sorry, this event has reached its maximum capacity.")
            return redirect('event_details', pk=pk)

    if request.method == 'POST':
        form = SelfRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                member = form.save(commit=False)
                member.event = event
                member.user = request.user
                member.name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
                member.email = request.user.email
                if is_waitlist:
                    member.status = 'Pending'
                else:
                    member.status = 'Active'
                member.save()
                
                if member.status == 'Active':
                    # Generate registration number
                    member.registration_number = f"REG-{event.id}-{member.id}"
                    member.save(update_fields=['registration_number'])
                    
                    # Generate Ticket
                    ticket = Ticket.objects.create(
                        member=member,
                        event=event,
                        ticket_number=f"TKT-{member.id}-{str(uuid.uuid4())[:8].upper()}",
                        status=Ticket.TicketStatus.ACTIVE
                    )
                    generate_ticket_qr(ticket)
                    generate_ticket_pdf(ticket)
                    ticket.save()
            
            if member.status == 'Active':
                # Send registration email task
                from .tasks import send_registration_email
                try:
                    send_registration_email.delay(member.id)
                except Exception:
                    pass
                
                messages.success(request, f"Successfully registered for {event.name}! Your ticket has been generated.")
                return redirect('registration_success', ticket_uuid=ticket.uuid)
            else:
                messages.info(request, f"Successfully joined the waiting list for {event.name}. We will notify you if a spot opens up!")
                return redirect('event_details', pk=pk)
    else:
        form = SelfRegistrationForm()

    return render(request, 'event/self-register.html', {
        'form': form,
        'event': event
    })

# ==========================================================================
# MEMBER CRUD
# ==========================================================================

@login_required
def member_list(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can view the registration list.")
    members = Member.objects.all().select_related('event').order_by('-created_at')
    
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"members_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Attendee Name', 'Email', 'Department', 'Role', 'Registered Event', 'Registration Date', 'Status']
        
        rows = []
        for m in members:
            rows.append([
                m.name,
                m.email,
                m.department,
                m.role,
                m.event.name,
                m.registration_date.strftime('%Y-%m-%d %H:%M') if m.registration_date else 'N/A',
                m.status
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Registered Members Directory",
                headers=headers,
                data=rows,
                col_widths=[100, 120, 80, 80, 130, 80, 50],
                landscape_mode=True,
                user=request.user.username,
                total_records=len(members)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
            
    return render(request, 'member/member-list.html', {'members': members})

@login_required
def joined_events(request):
    if request.user.is_staff:
        members = Member.objects.all().select_related('event', 'event__venue', 'event__category').order_by('-created_at')
    else:
        members = Member.objects.filter(
            Q(user=request.user) | Q(email__iexact=request.user.email if request.user.email else '___nonexistent___')
        ).select_related('event', 'event__venue', 'event__category').order_by('-created_at')
    return render(request, 'member/joined-events.html', {'members': members})

@login_required
def add_member(request):
    import uuid
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can manually add registrations.")
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                member = form.save(commit=False)
                event = member.event
                current_participants = Member.objects.filter(event=event, status='Active').count()
                if current_participants >= event.max_participants:
                    if event.waiting_list_enabled:
                        member.status = 'Pending'
                    else:
                        messages.error(request, "Event is at full capacity and waiting list is disabled.")
                        return render(request, 'member/add-member.html', {'form': form})
                else:
                    member.status = 'Active'
                
                member.save()
                
                # If active, generate ticket
                if member.status == 'Active':
                    if not member.registration_number:
                        member.registration_number = f"REG-{event.id}-{member.id}"
                        member.save(update_fields=['registration_number'])
                    ticket = Ticket.objects.create(
                        member=member,
                        event=event,
                        ticket_number=f"TKT-{member.id}-{str(uuid.uuid4())[:8].upper()}",
                        status=Ticket.TicketStatus.ACTIVE
                    )
                    generate_ticket_qr(ticket)
                    generate_ticket_pdf(ticket)
                    ticket.save()
            
            if member.status == 'Active':
                from .tasks import send_registration_email
                try:
                    send_registration_email.delay(member.id)
                except Exception:
                    pass
                messages.success(request, "Member Added Successfully")
            else:
                messages.info(request, "Event capacity reached. Member placed on waiting list.")
            return redirect('member_list')
    else:
        form = MemberForm()
    return render(request, 'member/add-member.html', {'form': form})

@login_required
def member_details(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if not request.user.is_staff and member.user != request.user and member.email.lower() != request.user.email.lower():
        raise PermissionDenied("You do not have permission to view this registration.")
    
    # Retrieve tickets associated with the member
    tickets = member.tickets.all()
    return render(request, 'member/member-details.html', {
        'member': member,
        'tickets': tickets
    })

@login_required
def edit_member(request, pk):
    import uuid
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can edit registration details.")
    member = get_object_or_404(Member, pk=pk)
    event = member.event
    old_status = member.status
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            member = form.save()
            # If status changed from Active to Inactive/Pending, run promotion
            if old_status == 'Active' and member.status != 'Active':
                promote_waiting_list(event)
            # If status changed from Inactive/Pending to Active and doesn't have a ticket, generate one
            elif old_status != 'Active' and member.status == 'Active':
                if not member.registration_number:
                    member.registration_number = f"REG-{event.id}-{member.id}"
                    member.save(update_fields=['registration_number'])
                ticket, created = Ticket.objects.get_or_create(
                    member=member,
                    event=event,
                    defaults={
                        'ticket_number': f"TKT-{member.id}-{str(uuid.uuid4())[:8].upper()}",
                        'status': Ticket.TicketStatus.ACTIVE
                    }
                )
                if created or not ticket.qr_code or not ticket.pdf_file:
                    generate_ticket_qr(ticket)
                    generate_ticket_pdf(ticket)
                    ticket.save()
            messages.success(request, "Member Updated Successfully")
            return redirect('member_list')
    else:
        form = MemberForm(instance=member)
    return render(request, 'member/edit-member.html', {'form': form, 'member': member})

@login_required
def delete_member(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete registration details.")
    member = get_object_or_404(Member, pk=pk)
    event = member.event
    if request.method == 'POST':
        member.delete()
        promote_waiting_list(event)
        messages.success(request, "Member Deleted Successfully")
        return redirect('member_list')
    return render(request, 'category/delete-category.html', {
        'delete_member_flag': True,
        'member': member
    })

# ==========================================================================
# REPORTS
# ==========================================================================

@login_required
def completed_events(request):
    events = Event.objects.filter(status='Completed').order_by('-start_date')
    return render(request, 'member/completed-events.html', {'events': events})

# ==========================================================================
# MESSAGING SYSTEM VIEWS
# ==========================================================================

def check_event_chat_permission(user, event):
    if user.is_superuser or user.is_staff:
        return True
    return Member.objects.filter(
        Q(user=user) | Q(email__iexact=user.email if user.email else '___nonexistent___'),
        event=event,
        status='Active'
    ).exists()

def get_chat_sidebar_data(user):
    User = get_user_model()
    # Retrieve all users except the current logged-in user
    all_users = User.objects.exclude(pk=user.pk).order_by('username')
    
    # Retrieve all events
    # Only list events the user can access to prevent security leakage in sidebar
    # Superusers/staff see all events. Others see events they are members of.
    if user.is_superuser or user.is_staff:
        all_events = Event.objects.all().order_by('name')
    else:
        user_emails = [user.email.lower()] if user.email else []
        member_event_ids = Member.objects.filter(email__in=user_emails, status='Active').values_list('event_id', flat=True)
        all_events = Event.objects.filter(pk__in=member_event_ids).order_by('name')
    
    # Retrieve active DM threads (users with whom messages exist)
    sent_recipients = Message.objects.filter(sender=user, recipient__isnull=False).values_list('recipient', flat=True)
    received_senders = Message.objects.filter(recipient=user).values_list('sender', flat=True)
    active_user_ids = set(list(sent_recipients) + list(received_senders))
    active_chats = User.objects.filter(pk__in=active_user_ids).order_by('username')
    
    # Calculate unread message counts for each user in active chats
    unread_counts = {}
    for chat_user in active_chats:
        unread_counts[chat_user.id] = Message.objects.filter(sender=chat_user, recipient=user, is_read=False).count()
        
    return {
        'all_users': all_users,
        'all_events': all_events,
        'active_chats': active_chats,
        'unread_counts': unread_counts,
    }

@login_required
def chat_dashboard(request):
    sidebar_data = get_chat_sidebar_data(request.user)
    unread_counts = sidebar_data.get('unread_counts', {})
    total_unread = sum(unread_counts.values()) if unread_counts else 0
    context = {
        **sidebar_data,
        'active_tab': 'dashboard',
        'total_unread': total_unread,
    }
    return render(request, 'chat/chat_dashboard.html', context)

@login_required
def direct_chat_view(request, user_id):
    User = get_user_model()
    recipient = get_object_or_404(User, pk=user_id)
    
    # Retrieve messages between the two users
    messages_list = Message.objects.filter(
        Q(sender=request.user, recipient=recipient) |
        Q(sender=recipient, recipient=request.user)
    ).order_by('created_at')
    
    # Mark incoming messages as read
    Message.objects.filter(sender=recipient, recipient=request.user, is_read=False).update(is_read=True)
    
    sidebar_data = get_chat_sidebar_data(request.user)
    context = {
        **sidebar_data,
        'recipient': recipient,
        'messages_list': messages_list,
        'active_tab': 'direct',
        'active_chat_user_id': recipient.id,
    }
    return render(request, 'chat/direct_chat.html', context)

@login_required
def event_chat_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    
    if not check_event_chat_permission(request.user, event):
        raise PermissionDenied("Access Denied: You are not registered for this event.")
        
    # Retrieve event group chat messages
    messages_list = Message.objects.filter(event=event).order_by('created_at')
    
    # Map of member emails to their roles
    members_map = {m.email.lower(): m.role for m in Member.objects.filter(event=event) if m.email}
    
    # Attach role to each message's sender
    for msg in messages_list:
        email = msg.sender.email.lower() if msg.sender.email else ""
        msg.sender_role = members_map.get(email, None)
    
    # Check if current user is registered as a member for the event (using user's email)
    member_record = Member.objects.filter(event=event, email__iexact=request.user.email).first() if request.user.email else None
    member_role = member_record.role if member_record else None
    
    sidebar_data = get_chat_sidebar_data(request.user)
    context = {
        **sidebar_data,
        'event': event,
        'messages_list': messages_list,
        'member_role': member_role,
        'active_tab': 'event',
        'active_event_id': event.id,
    }
    return render(request, 'chat/event_chat.html', context)

@login_required
def send_direct_message(request, user_id):
    if request.method == 'POST':
        User = get_user_model()
        recipient = get_object_or_404(User, pk=user_id)
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(sender=request.user, recipient=recipient, content=content)
    return redirect('direct_chat', user_id=user_id)

@login_required
def send_event_message(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(Event, pk=event_id)
        if not check_event_chat_permission(request.user, event):
            raise PermissionDenied("Access Denied: You are not registered for this event.")
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(sender=request.user, event=event, content=content)
    return redirect('event_chat', event_id=event_id)

@login_required
def mark_messages_read(request, user_id):
    User = get_user_model()
    sender = get_object_or_404(User, pk=user_id)
    Message.objects.filter(sender=sender, recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.http import JsonResponse
        return JsonResponse({'status': 'success'})
    return redirect('direct_chat', user_id=user_id)

# ==========================================================================
# VENUE CRUD VIEWS
# ==========================================================================

@login_required
def venue_list(request):
    venues = Venue.objects.filter(is_active=True).order_by('name')
    
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"venues_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Venue Name', 'Location/Address', 'Capacity', 'Type']
        
        rows = []
        for v in venues:
            rows.append([
                v.name,
                v.location,
                v.capacity,
                v.venue_type
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Venues Directory Report",
                headers=headers,
                data=rows,
                col_widths=[150, 200, 80, 110],
                landscape_mode=False,
                user=request.user.username,
                total_records=len(venues)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response

    for venue in venues:
        if venue.available_from and venue.available_to:
            venue.hours_display = f'{venue.available_from.strftime("%I:%M %p")} - {venue.available_to.strftime("%I:%M %p")}'
        else:
            venue.hours_display = 'All Day'
            
    return render(request, 'venue/venue_list.html', {
        'venues': venues,
        'can_export_options': request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'role', '') in ['admin', 'organizer'],
    })

@login_required
def venue_details(request, pk):
    venue = get_object_or_404(Venue, pk=pk)
    associated_events = venue.events.all().order_by('start_date')
    return render(request, 'venue/venue_details.html', {
        'venue': venue,
        'associated_events': associated_events
    })

@login_required
def create_venue(request):
    if request.method == 'POST':
        form = VenueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Venue Created Successfully")
            return redirect('venue_list')
    else:
        form = VenueForm()
    return render(request, 'venue/create_venue.html', {'form': form})

@login_required
def edit_venue(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can edit venues.")
    venue = get_object_or_404(Venue, pk=pk)
    if request.method == 'POST':
        form = VenueForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
            messages.success(request, "Venue Updated Successfully")
            return redirect('venue_list')
    else:
        form = VenueForm(instance=venue)
    return render(request, 'venue/edit_venue.html', {'form': form, 'venue': venue})

@login_required
def delete_venue(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete venues.")
    venue = get_object_or_404(Venue, pk=pk)
    if request.method == 'POST':
        venue.is_active = False
        venue.save()
        messages.success(request, "Venue Archived Successfully")
        return redirect('venue_list')
    return render(request, 'venue/delete_venue.html', {'venue': venue})


# ==========================================================================
# RESOURCE CRUD & ALLOCATION VIEWS
# ==========================================================================

@login_required
def resource_list(request):
    resources = Resource.objects.filter(is_active=True).order_by('name')
    from django.db.models import Sum
    for resource in resources:
        allocations_sum = ResourceAllocation.objects.filter(
            resource=resource,
            event__status__in=['Active', 'Pending']
        ).aggregate(Sum('allocated_quantity'))['allocated_quantity__sum'] or 0
        resource.allocated_count = allocations_sum
        resource.available_count = max(0, resource.total_quantity - allocations_sum)

    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"resources_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Resource Name', 'Total Quantity', 'Allocated Quantity', 'Available Quantity', 'Type']
        
        rows = []
        for r in resources:
            rows.append([
                r.name,
                r.total_quantity,
                r.allocated_count,
                r.available_count,
                r.resource_type
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Inventory Resources Report",
                headers=headers,
                data=rows,
                col_widths=[150, 90, 90, 90, 110],
                landscape_mode=False,
                user=request.user.username,
                total_records=len(resources)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
            
    allocations = ResourceAllocation.objects.all().order_by('-allocated_at')
    return render(request, 'resource/resource_list.html', {
        'resources': resources,
        'allocations': allocations
    })

@login_required
def create_resource(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can create resources.")
    if request.method == 'POST':
        form = ResourceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Resource Created Successfully")
            return redirect('resource_list')
    else:
        form = ResourceForm()
    return render(request, 'resource/create_resource.html', {'form': form})

@login_required
def edit_resource(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can edit resources.")
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == 'POST':
        form = ResourceForm(request.POST, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, "Resource Updated Successfully")
            return redirect('resource_list')
    else:
        form = ResourceForm(instance=resource)
    return render(request, 'resource/edit_resource.html', {'form': form, 'resource': resource})

@login_required
def delete_resource(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete resources.")
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == 'POST':
        resource.delete()
        messages.success(request, "Resource Deleted Successfully")
        return redirect('resource_list')
    return render(request, 'resource/delete_resource.html', {'resource': resource})

@login_required
def allocate_resource(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can allocate resources.")
    if request.method == 'POST':
        form = ResourceAllocationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Resource Allocated Successfully")
            return redirect('resource_list')
    else:
        form = ResourceAllocationForm()
    return render(request, 'resource/allocate_resource.html', {'form': form})

@login_required
def delete_allocation(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can remove resource allocations.")
    allocation = get_object_or_404(ResourceAllocation, pk=pk)
    if request.method == 'POST':
        allocation.delete()
        messages.success(request, "Resource Allocation Removed Successfully")
        return redirect('resource_list')
    return render(request, 'category/delete-category.html', {
        'delete_allocation_flag': True,
        'allocation': allocation
    })


# ==========================================================================
# SPONSOR CRUD VIEWS
# ==========================================================================

@login_required
def sponsor_list(request):
    sponsors = Sponsor.objects.filter(is_active=True).order_by('name')
    
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"sponsors_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Sponsor Name', 'Sponsorship Level', 'Contribution Amount ($)', 'Contact Person']
        
        rows = []
        for s in sponsors:
            rows.append([
                s.name,
                s.sponsorship_level,
                float(s.contribution_amount) if s.contribution_amount else 0.0,
                s.contact_person or 'N/A'
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Event Sponsors Directory",
                headers=headers,
                data=rows,
                col_widths=[150, 110, 110, 130],
                landscape_mode=False,
                user=request.user.username,
                total_records=len(sponsors)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
            
    return render(request, 'sponsor/sponsor_list.html', {'sponsors': sponsors})

@login_required
def create_sponsor(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can register sponsors.")
    if request.method == 'POST':
        form = SponsorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Sponsor Registered Successfully")
            return redirect('sponsor_list')
    else:
        form = SponsorForm()
    return render(request, 'sponsor/create_sponsor.html', {'form': form})

@login_required
def edit_sponsor(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can edit sponsors.")
    sponsor = get_object_or_404(Sponsor, pk=pk)
    if request.method == 'POST':
        form = SponsorForm(request.POST, request.FILES, instance=sponsor)
        if form.is_valid():
            form.save()
            messages.success(request, "Sponsor Updated Successfully")
            return redirect('sponsor_list')
    else:
        form = SponsorForm(instance=sponsor)
    return render(request, 'sponsor/edit_sponsor.html', {'form': form, 'sponsor': sponsor})

@login_required
def delete_sponsor(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete sponsors.")
    sponsor = get_object_or_404(Sponsor, pk=pk)
    if request.method == 'POST':
        sponsor.delete()
        messages.success(request, "Sponsor Deleted Successfully")
        return redirect('sponsor_list')
    return render(request, 'category/delete-category.html', {
        'delete_sponsor_flag': True,
        'sponsor': sponsor
    })



# ==========================================================================
# VENDOR & CONTRACT CRUD VIEWS
# ==========================================================================

@login_required
def vendor_list(request):
    vendors = Vendor.objects.filter(is_active=True).order_by('name')
    
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"vendors_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Vendor Name', 'Contact Person', 'Email', 'Phone', 'Service Type']
        
        rows = []
        for v in vendors:
            rows.append([
                v.name,
                v.contact_person or 'N/A',
                v.email or 'N/A',
                v.phone or 'N/A',
                v.service_type or 'N/A'
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Service Vendors Registry",
                headers=headers,
                data=rows,
                col_widths=[120, 100, 130, 90, 100],
                landscape_mode=True,
                user=request.user.username,
                total_records=len(vendors)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
            
    return render(request, 'vendor/vendor_list.html', {'vendors': vendors})

@login_required
def create_vendor(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can register vendors.")
    if request.method == 'POST':
        form = VendorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vendor Registered Successfully")
            return redirect('vendor_list')
    else:
        form = VendorForm()
    return render(request, 'vendor/create_vendor.html', {'form': form})

@login_required
def edit_vendor(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can edit vendors.")
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == 'POST':
        form = VendorForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, "Vendor Updated Successfully")
            return redirect('vendor_list')
    else:
        form = VendorForm(instance=vendor)
    return render(request, 'vendor/edit_vendor.html', {'form': form, 'vendor': vendor})

@login_required
def delete_vendor(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete vendors.")
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == 'POST':
        vendor.is_active = False
        vendor.save()
        messages.success(request, "Vendor Archived Successfully")
        return redirect('vendor_list')
    return render(request, 'vendor/delete_vendor.html', {'vendor': vendor})

@login_required
def contract_list(request):
    contracts = Contract.objects.all().select_related('vendor', 'event').order_by('-created_at')
    
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"contracts_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Vendor Name', 'Associated Event', 'Contract Cost ($)', 'Status', 'Start Date', 'End Date']
        
        rows = []
        for c in contracts:
            rows.append([
                c.vendor.name,
                c.event.name,
                float(c.contract_amount),
                c.status,
                c.start_date.strftime('%Y-%m-%d'),
                c.end_date.strftime('%Y-%m-%d')
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Vendor Contracts Report",
                headers=headers,
                data=rows,
                col_widths=[120, 150, 90, 70, 70, 70],
                landscape_mode=True,
                user=request.user.username,
                total_records=len(contracts)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
            
    return render(request, 'contract/contract_list.html', {'contracts': contracts})

@login_required
def create_contract(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can manage contracts.")
    if request.method == 'POST':
        form = ContractForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Contract Created Successfully")
            return redirect('contract_list')
    else:
        form = ContractForm()
    return render(request, 'contract/create_contract.html', {'form': form})

@login_required
def edit_contract(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can edit contracts.")
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == 'POST':
        form = ContractForm(request.POST, request.FILES, instance=contract)
        if form.is_valid():
            form.save()
            messages.success(request, "Contract Updated Successfully")
            return redirect('contract_list')
    else:
        form = ContractForm(instance=contract)
    return render(request, 'contract/edit_contract.html', {'form': form, 'contract': contract})

@login_required
def delete_contract(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete contracts.")
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == 'POST':
        contract.delete()
        messages.success(request, "Contract Deleted Successfully")
        return redirect('contract_list')
    return render(request, 'category/delete-category.html', {
        'delete_contract_flag': True,
        'contract': contract
    })


# ==========================================================================
# BUDGET & EXPENSE CRUD VIEWS
# ==========================================================================

@login_required
def budget_list(request):
    budgets = Budget.objects.all().select_related('event').order_by('event__start_date')
    from django.db.models import Sum
    for b in budgets:
        b.total_spent = b.expenses.filter(approved=True).aggregate(Sum('amount'))['amount__sum'] or 0
        b.total_pending = b.expenses.filter(approved=False).aggregate(Sum('amount'))['amount__sum'] or 0
        b.remaining = max(0, b.total_amount - b.total_spent)
        b.spent_percent = int((b.total_spent / b.total_amount) * 100) if b.total_amount > 0 else 0
        b.pending_percent = int((b.total_pending / b.total_amount) * 100) if b.total_amount > 0 else 0
        
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"budgets_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Event Name', 'Total Budget ($)', 'Total Spent ($)', 'Total Pending ($)', 'Remaining Balance ($)', 'Spent %']
        
        rows = []
        for b in budgets:
            rows.append([
                b.event.name,
                float(b.total_amount),
                float(b.total_spent),
                float(b.total_pending),
                float(b.remaining),
                f"{b.spent_percent}%"
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Financial Budgets Summary Report",
                headers=headers,
                data=rows,
                col_widths=[180, 80, 80, 80, 80, 60],
                landscape_mode=True,
                user=request.user.username,
                total_records=len(budgets)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
            
    return render(request, 'budget/budget_list.html', {'budgets': budgets})

@login_required
def budget_details(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    expenses = budget.expenses.all().order_by('-created_at')
    from django.db.models import Sum
    total_spent = budget.expenses.filter(approved=True).aggregate(Sum('amount'))['amount__sum'] or 0
    total_pending = budget.expenses.filter(approved=False).aggregate(Sum('amount'))['amount__sum'] or 0
    remaining = budget.total_amount - total_spent
    spent_percent = int((total_spent / budget.total_amount) * 100) if budget.total_amount > 0 else 0
    pending_percent = int((total_pending / budget.total_amount) * 100) if budget.total_amount > 0 else 0
    return render(request, 'budget/budget_details.html', {
        'budget': budget,
        'expenses': expenses,
        'total_spent': total_spent,
        'total_pending': total_pending,
        'remaining': remaining,
        'spent_percent': spent_percent,
        'pending_percent': pending_percent
    })

@login_required
def create_budget(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can create budgets.")
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Budget Created Successfully")
            return redirect('budget_list')
    else:
        form = BudgetForm()
    return render(request, 'budget/create_budget.html', {'form': form})

@login_required
def delete_budget(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete budgets.")
    budget = get_object_or_404(Budget, pk=pk)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, "Budget Deleted Successfully")
        return redirect('budget_list')
    return render(request, 'category/delete-category.html', {
        'delete_budget_flag': True,
        'budget': budget
    })

@login_required
def create_expense(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can log expenses.")
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense Logged Successfully")
            return redirect('budget_details', pk=form.cleaned_data['budget'].id)
    else:
        budget_id = request.GET.get('budget')
        initial_data = {}
        if budget_id:
            initial_data['budget'] = budget_id
        form = ExpenseForm(initial=initial_data)
    return render(request, 'budget/create_expense.html', {'form': form})

@login_required
def approve_expense(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can authorize expenses.")
    expense = get_object_or_404(Expense, pk=pk)
    expense.approved = True
    expense.save()
    messages.success(request, "Expense Approved & Authorized Successfully")
    return redirect('budget_details', pk=expense.budget.id)

@login_required
def delete_expense(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can delete expenses.")
    expense = get_object_or_404(Expense, pk=pk)
    budget_id = expense.budget.id
    if request.method == 'POST':
        expense.delete()
        messages.success(request, "Expense Deleted Successfully")
        return redirect('budget_details', pk=budget_id)
    return render(request, 'category/delete-category.html', {
        'delete_expense_flag': True,
        'expense': expense
    })


# ==========================================================================
# GLOBAL SEARCH API
# ==========================================================================

@login_required
def global_search(request):
    """Live search endpoint — returns JSON results for navbar & command palette."""
    query = request.GET.get('q', '').strip()
    results = []

    if len(query) >= 2:
        # Events
        events = Event.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).select_related('category', 'venue')[:5]
        for e in events:
            results.append({
                'type': 'Event',
                'icon': 'bi-calendar-event-fill',
                'title': e.name,
                'subtitle': f"{e.category.name} · {e.status}",
                'url': f'/event/{e.pk}/',
            })

        # Members
        members = Member.objects.filter(
            Q(name__icontains=query) | Q(email__icontains=query) | Q(department__icontains=query)
        )[:4]
        for m in members:
            results.append({
                'type': 'Member',
                'icon': 'bi-person-fill',
                'title': m.name,
                'subtitle': f"{m.department} · {m.year}",
                'url': f'/member/{m.pk}/',
            })

        # Categories
        categories = Category.objects.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )[:3]
        for c in categories:
            results.append({
                'type': 'Category',
                'icon': 'bi-tags-fill',
                'title': c.name,
                'subtitle': f"Code: {c.code} · {c.status}",
                'url': f'/category/{c.pk}/',
            })

        # Venues
        venues = Venue.objects.filter(
            Q(name__icontains=query) | Q(location__icontains=query)
        )[:3]
        for v in venues:
            results.append({
                'type': 'Venue',
                'icon': 'bi-geo-alt-fill',
                'title': v.name,
                'subtitle': f"{v.location} · Cap: {v.capacity}",
                'url': f'/venue/{v.pk}/',
            })

    return JsonResponse({'query': query, 'results': results, 'count': len(results)})

@csrf_exempt
@login_required
def update_preferences_api(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON body.'}, status=400)

        # Get or create UserProfile
        from .models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        # Update styling options if present
        if 'theme' in data:
            theme = data['theme'].strip().lower()
            if theme in dict(UserProfile.THEME_CHOICES):
                profile.theme_preference = theme
        if 'accent' in data:
            accent = data['accent'].strip().lower()
            if accent in dict(UserProfile.ACCENT_CHOICES):
                profile.accent_color = accent
        if 'font' in data:
            font = data['font'].strip().lower()
            if font in dict(UserProfile.FONT_CHOICES):
                profile.font = font
        if 'border_radius' in data:
            radius = data['border_radius'].strip().lower()
            if radius in dict(UserProfile.BORDER_RADIUS_CHOICES):
                profile.border_radius = radius
        if 'compact' in data:
            profile.compact_mode = bool(data['compact'])
        if 'animations' in data:
            profile.animations_enabled = bool(data['animations'])
        if 'reduced_motion' in data:
            profile.reduced_motion = bool(data['reduced_motion'])

        # Save profile preferences
        profile.save()
        return JsonResponse({'status': 'success', 'message': 'Preferences saved successfully.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid HTTP request method.'}, status=405)


# ==========================================================================
# PHASE 3: ATTENDEE & TICKET SYSTEM VIEWS
# ==========================================================================

@login_required
def registration_success(request, ticket_uuid):
    ticket = get_object_or_404(Ticket, uuid=ticket_uuid)
    # Security: check if requesting user is staff, organizer of the event, or owner of the ticket
    is_authorized = (
        request.user.is_staff or
        ticket.event.organizers.filter(pk=request.user.pk).exists() or
        ticket.member.user == request.user or
        ticket.member.email.lower() == request.user.email.lower()
    )
    if not is_authorized:
        raise PermissionDenied("You do not have permission to view this registration ticket.")
    return render(request, 'event/registration-success.html', {
        'ticket': ticket,
        'member': ticket.member,
        'event': ticket.event
    })

@login_required
def ticket_list(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can view the ticket directory.")
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    tickets = Ticket.objects.all().select_related('member', 'event').order_by('-issue_date')
    if query:
        tickets = tickets.filter(
            Q(ticket_number__icontains=query) |
            Q(member__name__icontains=query) |
            Q(member__email__icontains=query) |
            Q(member__registration_number__icontains=query) |
            Q(uuid__icontains=query)
        )
    if status_filter:
        tickets = tickets.filter(status=status_filter)
        
    # Export Handling
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"tickets_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Ticket ID', 'Attendee Name', 'Registered Event', 'Issue Date', 'Status']
        
        rows = []
        for ticket in tickets:
            rows.append([
                ticket.ticket_number,
                ticket.member.name,
                ticket.event.name,
                ticket.issue_date.strftime('%Y-%m-%d %H:%M') if ticket.issue_date else 'N/A',
                ticket.status
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Tickets & Access Passes Directory",
                headers=headers,
                data=rows,
                col_widths=[120, 120, 150, 90, 60],
                landscape_mode=False,
                user=request.user.username,
                total_records=len(tickets)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response
            
    return render(request, 'ticket/ticket-list.html', {
        'tickets': tickets,
        'query': query,
        'status_filter': status_filter
    })

@login_required
def ticket_details(request, uuid_val):
    # Retrieve ticket
    ticket = get_object_or_404(Ticket, uuid=uuid_val)
    # Check permissions
    is_staff = request.user.is_staff
    is_org = ticket.event.organizers.filter(pk=request.user.pk).exists()
    is_authorized = (
        is_staff or
        is_org or
        ticket.member.user == request.user or
        ticket.member.email.lower() == request.user.email.lower()
    )
    if not is_authorized:
        raise PermissionDenied("You do not have permission to view this ticket details.")
    return render(request, 'ticket/ticket-details.html', {
        'ticket': ticket,
        'is_manager': (is_staff or is_org)
    })

@login_required
def reset_ticket_checkin(request, uuid_val):
    ticket = get_object_or_404(Ticket, uuid=uuid_val)
    is_authorized = (
        request.user.is_staff or
        ticket.event.organizers.filter(pk=request.user.pk).exists()
    )
    if not is_authorized:
        raise PermissionDenied("You do not have permission to reset this ticket.")
    
    if request.method == 'POST':
        from .models import Attendance
        # 1. Delete associated attendance record(s)
        Attendance.objects.filter(member=ticket.member, event=ticket.event).delete()
        
        # 2. Reset member check-in timestamp
        ticket.member.check_in_time = None
        ticket.member.save(update_fields=['check_in_time'])
        
        # 3. Set ticket status back to Active
        ticket.status = Ticket.TicketStatus.ACTIVE
        ticket.save(update_fields=['status'])
        
        messages.success(request, f"Check-in for {ticket.member.name} has been successfully reset. The ticket is now active again.")
    return redirect('ticket_details', uuid_val=ticket.uuid)


@login_required
def download_ticket_pdf(request, uuid_val):
    from django.http import HttpResponse, Http404
    ticket = get_object_or_404(Ticket, uuid=uuid_val)
    is_authorized = (
        request.user.is_staff or
        ticket.event.organizers.filter(pk=request.user.pk).exists() or
        ticket.member.user == request.user or
        ticket.member.email.lower() == request.user.email.lower()
    )
    if not is_authorized:
        raise PermissionDenied("You do not have permission to download this ticket.")
    
    if not ticket.pdf_file:
        generate_ticket_pdf(ticket)
        ticket.save()
        
    try:
        response = HttpResponse(ticket.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'
        return response
    except Exception:
        raise Http404("PDF Ticket file not found.")

@login_required
def attendance_list(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only staff members can view attendance rosters.")
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    attendance_records = Attendance.objects.all().select_related('event', 'member', 'verified_by').order_by('-check_in_time')
    if query:
        attendance_records = attendance_records.filter(
            Q(member__name__icontains=query) |
            Q(event__name__icontains=query) |
            Q(member__email__icontains=query)
        )
    if status_filter:
        attendance_records = attendance_records.filter(status=status_filter)
        
    # Export trigger
    export_type = request.GET.get('export')
    if export_type in ['csv', 'pdf']:
        check_export_permission(request)
        
        filename_base = f"attendance_report_{timezone.now().strftime('%Y-%m-%d')}"
        headers = ['Event', 'Attendee Name', 'Email', 'Check-In Time', 'Status', 'Verified By', 'Device']
        
        rows = []
        for record in attendance_records:
            rows.append([
                record.event.name,
                record.member.name,
                record.member.email,
                record.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if record.check_in_time else 'N/A',
                record.status,
                record.verified_by.username if record.verified_by else 'System',
                record.verification_device or 'Unknown'
            ])
            
        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
            write_csv_with_bom(response, headers, rows)
            return response
        elif export_type == 'pdf':
            pdf_buffer = generate_pdf_report(
                title="Attendance Roster Report",
                headers=headers,
                data=rows,
                col_widths=[120, 100, 120, 100, 60, 80, 80],
                landscape_mode=True,
                user=request.user.username,
                total_records=len(attendance_records)
            )
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
            return response

    return render(request, 'attendance/attendance-list.html', {
        'attendance_records': attendance_records,
        'query': query,
        'status_filter': status_filter
    })

@login_required
def qr_scanner_view(request):
    # Only staff or designated organizers can access the scanner
    user_role = getattr(getattr(request.user, 'profile', None), 'role', 'viewer')
    if not request.user.is_staff and user_role not in ['admin', 'organizer']:
        # Check if the user is organizer of at least one event
        if not Event.objects.filter(organizers=request.user).exists():
            raise PermissionDenied("Only event coordinators and staff can access the check-in scanner.")
    return render(request, 'event/qr-scanner.html')

# ==========================================================================
# PHASE 3: ATTENDEE & TICKET SYSTEM APIs
# ==========================================================================

@login_required
def api_register_list(request):
    # REST API listing registrations for organizers
    if not request.user.is_staff and not Event.objects.filter(organizers=request.user).exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    members = Member.objects.all().order_by('-registration_date')
    event_id = request.GET.get('event_id')
    if event_id:
        members = members.filter(event_id=event_id)
        
    data = []
    for m in members:
        data.append({
            'id': m.id,
            'name': m.name,
            'email': m.email,
            'department': m.department,
            'role': m.role,
            'status': m.status,
            'registration_number': m.registration_number,
        })
    return JsonResponse(data, safe=False)

@login_required
def api_checkin(request):
    import json
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)
        
    # Permission validation
    is_staff_or_organizer = request.user.is_staff or Event.objects.filter(organizers=request.user).exists()
    if not is_staff_or_organizer:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    try:
        data = json.loads(request.body)
        ticket_uuid = data.get('uuid')
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)
        
    if not ticket_uuid:
        return JsonResponse({'status': 'error', 'message': 'Missing ticket UUID'}, status=400)
        
    try:
        ticket = Ticket.objects.select_related('member', 'event').get(uuid=ticket_uuid)
    except Ticket.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid ticket. Access Denied.'}, status=404)
        
    # Validate ticket status
    if ticket.status == Ticket.TicketStatus.USED:
        # Fetch checkin record details to be extra helpful
        checkin_time_str = "Unknown"
        attendance = Attendance.objects.filter(member=ticket.member, event=ticket.event).first()
        if attendance:
            checkin_time_str = attendance.check_in_time.strftime('%I:%M %p, %d %b %Y')
        return JsonResponse({
            'status': 'error', 
            'message': f'Ticket already used! Checked in at {checkin_time_str}.',
            'member_name': ticket.member.name,
            'event_name': ticket.event.name
        }, status=400)
        
    if ticket.status == Ticket.TicketStatus.CANCELLED:
        return JsonResponse({'status': 'error', 'message': 'Ticket has been cancelled.'}, status=400)
        
    # Expired check
    if ticket.expiry_date and ticket.expiry_date < timezone.now():
        return JsonResponse({'status': 'error', 'message': 'Ticket has expired.'}, status=400)
        
    # Check-in processing
    ticket.status = Ticket.TicketStatus.USED
    ticket.save(update_fields=['status'])
    
    # Log details to Member
    ticket.member.check_in_time = timezone.now()
    ticket.member.save(update_fields=['check_in_time'])
    
    # Create Attendance log record
    attendance = Attendance.objects.create(
        event=ticket.event,
        member=ticket.member,
        check_in_time=timezone.now(),
        status=Attendance.AttendanceStatus.PRESENT,
        verified_by=request.user,
        verification_device='Webcam Scanner'
    )
    
    return JsonResponse({
        'status': 'success',
        'message': 'Check-in successful!',
        'member_name': ticket.member.name,
        'event_name': ticket.event.name,
        'registration_number': ticket.member.registration_number,
        'check_in_time': attendance.check_in_time.strftime('%I:%M %p')
    })

@login_required
def api_attendance_log(request):
    if not request.user.is_staff and not Event.objects.filter(organizers=request.user).exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    records = Attendance.objects.all().order_by('-check_in_time')
    event_id = request.GET.get('event_id')
    if event_id:
        records = records.filter(event_id=event_id)
        
    data = []
    for r in records:
        data.append({
            'event_name': r.event.name,
            'member_name': r.member.name,
            'check_in_time': r.check_in_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': r.status,
            'verified_by': r.verified_by.username if r.verified_by else 'System',
            'device': r.verification_device
        })
    return JsonResponse(data, safe=False)

@login_required
def event_waiting_list(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not request.user.is_staff and not event.organizers.filter(pk=request.user.pk).exists():
        raise PermissionDenied("Only event coordinators and staff can view the waiting list.")
    waiting_members = Member.objects.filter(event=event, status='Pending').order_by('registration_date')
    return render(request, 'event/waiting-list.html', {
        'event': event,
        'waiting_members': waiting_members
    })


# ==========================================================================
# SYSTEM ERROR VIEWS
# ==========================================================================

def custom_404_view(request, exception):
    return render(request, 'errors/404.html', status=404)

def custom_500_view(request):
    return render(request, 'errors/500.html', status=500)

def custom_403_view(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def custom_400_view(request, exception=None):
    return render(request, 'errors/400.html', status=400)

# ==========================================================================
# FOR CHATBOT AI
# ==========================================================================

@login_required
def ai_chat(request):
    if request.method == 'GET':
        return render(request, 'chat/ai_chat.html')

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are supported.'}, status=405)

    message = request.POST.get("message", "").strip()

    if not message:
        return JsonResponse({"error": "Please enter a message."}, status=400)

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return JsonResponse(
            {"error": "The AI assistant is not configured. Add OPENAI_API_KEY to your .env file."},
            status=503,
        )

    try:
        client = OpenAI(api_key=api_key)
        events = Event.objects.filter(
            visibility=Event.Visibility.PUBLIC,
            status__in=[Event.EventStatus.ACTIVE, Event.EventStatus.PENDING],
            end_date__gte=date.today(),
        ).select_related('category', 'venue').order_by('start_date')[:50]
        event_context = '\n'.join(
            f"- {event.name}: {event.start_date} to {event.end_date}; "
            f"category {event.category.name}; venue {event.venue.name if event.venue else 'TBD'}"
            for event in events
        ) or 'No upcoming public events are currently listed.'

        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=(
                "You are EventOS AI Assistant. Help users with college "
                "events, registration, tickets, venues, attendance and "
                "other EventOS features. Give clear and concise answers. "
                "Only state event facts supported by the supplied data. "
                "If the data does not answer the question, say so clearly.\n\n"
                f"Upcoming public events:\n{event_context}"
            ),
            input=message
        )

        return JsonResponse({"reply": response.output_text})

    except RateLimitError:
        return JsonResponse(
            {"error": "The OpenAI account has no API credits remaining. Add credits or use a funded API key."},
            status=503,
        )
    except AuthenticationError:
        return JsonResponse(
            {"error": "The OpenAI API key is invalid or revoked. Create a new key and update .env."},
            status=503,
        )
    except Exception:
        logger.exception("AI assistant request failed")
        return JsonResponse(
            {"error": "The AI assistant is temporarily unavailable. Check the server logs for details."},
            status=503,
        )