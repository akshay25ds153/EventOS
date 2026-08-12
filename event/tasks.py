from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Member, Event

@shared_task
def send_registration_email(member_id):
    """
    Sends a confirmation email to a newly registered member.
    """
    try:
        member = Member.objects.get(pk=member_id)
        subject = f"Registration Confirmed: {member.event.name}"
        message = (
            f"Hello {member.name},\n\n"
            f"Your registration for the event '{member.event.name}' has been successfully confirmed!\n\n"
            f"Event Details:\n"
            f"- Date: {member.event.start_date}\n"
            f"- Time: {member.event.start_time}\n"
            f"- Venue: {member.event.venue.name} ({member.event.venue.location})\n"
            f"- Assigned Role: {member.role}\n\n"
            f"You can download your scannable check-in ticket by logging into the platform.\n\n"
            f"Best regards,\n"
            f"The EventSphere Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL or 'no-reply@eventsphere.com',
            recipient_list=[member.email],
            fail_silently=False
        )
        return f"Successfully sent registration email to {member.email}"
    except Member.DoesNotExist:
        return f"Member with ID {member_id} does not exist"

@shared_task
def send_event_reminders():
    """
    Finds all events scheduled to start tomorrow (in 24 hours) and
    sends pre-event reminder notifications to all registered members.
    """
    tomorrow = timezone.localdate() + timedelta(days=1)
    upcoming_events = Event.objects.filter(start_date=tomorrow, status='Active')
    
    email_count = 0
    for event in upcoming_events:
        members = Member.objects.filter(event=event, status='Active')
        for member in members:
            subject = f"Reminder: '{event.name}' starts tomorrow!"
            message = (
                f"Hello {member.name},\n\n"
                f"This is a quick reminder that the event '{event.name}' is scheduled to start tomorrow, "
                f"{event.start_date} at {event.start_time}.\n\n"
                f"Location:\n"
                f"- Venue: {event.venue.name} ({event.venue.location})\n\n"
                f"Please ensure you have your ticket QR code ready for check-in at the entrance.\n\n"
                f"We look forward to seeing you there!\n\n"
                f"Best regards,\n"
                f"The EventSphere Team"
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'no-reply@eventsphere.com',
                recipient_list=[member.email],
                fail_silently=True
            )
            email_count += 1
            
    return f"Dispatched {email_count} event reminders for tomorrow's events ({tomorrow})"
