from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone



class LoginViewTests(TestCase):
    def test_login_accepts_email_as_username(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username='eventmanager',
            email='manager@example.com',
            password='Secret123!'
        )

        response = self.client.post(
            reverse('login'),
            {'username': 'manager@example.com', 'password': 'Secret123!'},
            follow=True
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)


from .models import Category, Event, Message, Venue, Member, Ticket, Vendor, Contract, UserProfile
from .forms import MemberForm

class MemberFormTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Testing",
            code="CAT-TEST",
            description="Testing category",
            priority="Medium",
            status="Active"
        )
        self.venue = Venue.objects.create(
            name="Test Venue",
            capacity=100,
            location="Test Location"
        )
        self.event = Event.objects.create(
            name="Test Event",
            category=self.category,
            venue=self.venue,
            start_date="2026-08-01",
            end_date="2026-08-02",
            start_time="09:00:00",
            end_time="17:00:00",
            max_participants=100,
            registration_deadline="2026-07-31",
            description="Test Description",
            status="Active"
        )

    def test_organizer_does_not_require_year(self):
        form_data = {
            'name': 'Test Organizer',
            'email': 'organizer@example.com',
            'phone': '1234567890',
            'department': 'CS',
            'year': '',
            'event': self.event.id,
            'role': 'Organizer',
            'status': 'Active'
        }
        form = MemberForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_participant_requires_year(self):
        form_data = {
            'name': 'Test Participant',
            'email': 'participant@example.com',
            'phone': '1234567890',
            'department': 'CS',
            'year': '',
            'event': self.event.id,
            'role': 'Participant',
            'status': 'Active'
        }
        form = MemberForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)

    def test_volunteer_requires_year(self):
        form_data = {
            'name': 'Test Volunteer',
            'email': 'volunteer@example.com',
            'phone': '1234567890',
            'department': 'CS',
            'year': '',
            'event': self.event.id,
            'role': 'Volunteer',
            'status': 'Active'
        }
        form = MemberForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('year', form.errors)


class MessagingTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user_a = self.User.objects.create_user(
            username='usera',
            email='usera@example.com',
            password='Password123'
        )
        self.user_b = self.User.objects.create_user(
            username='userb',
            email='userb@example.com',
            password='Password123'
        )
        self.category = Category.objects.create(
            name="General",
            code="CAT-GEN",
            description="General category",
            priority="Medium",
            status="Active"
        )
        self.venue = Venue.objects.create(
            name="Main Hall",
            capacity=50,
            location="Main Hall Location"
        )
        self.event = Event.objects.create(
            name="General Event",
            category=self.category,
            venue=self.venue,
            start_date="2026-08-01",
            end_date="2026-08-02",
            start_time="09:00:00",
            end_time="17:00:00",
            max_participants=50,
            registration_deadline="2026-07-31",
            status="Active"
        )
        # Register user_a as a member of the event
        from .models import Member
        self.member_a = Member.objects.create(
            name="User A",
            email=self.user_a.email,
            phone="1234567890",
            department="CS",
            year="1st",
            event=self.event,
            role="Participant",
            status="Active"
        )

    def test_unauthenticated_user_cannot_access_chat(self):
        response = self.client.get(reverse('chat_dashboard'))
        self.assertRedirects(response, f"/login/?next={reverse('chat_dashboard')}")

    def test_ai_assistant_page_requires_login(self):
        response = self.client.get(reverse('ai_chat'))
        self.assertRedirects(response, f"/login/?next={reverse('ai_chat')}")

    def test_ai_assistant_reports_missing_api_key(self):
        self.client.login(username='usera', password='Password123')
        with self.settings(OPENAI_API_KEY=None):
            response = self.client.post(reverse('ai_chat'), {'message': 'What events are available?'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('OPENAI_API_KEY', response.json()['error'])

    def test_direct_message_creation_and_unread_count(self):
        self.client.login(username='usera', password='Password123')
        
        # Initially 0 unread
        response = self.client.get(reverse('chat_dashboard'))
        self.assertEqual(response.context['total_unread_messages'], 0)
        
        # User B sends message to User A
        Message.objects.create(sender=self.user_b, recipient=self.user_a, content="Hello User A")
        
        # A should now have 1 unread message
        response = self.client.get(reverse('chat_dashboard'))
        self.assertEqual(response.context['total_unread_messages'], 1)
        
        # Visit direct chat with B to mark read
        chat_response = self.client.get(reverse('direct_chat', args=[self.user_b.id]))
        self.assertEqual(chat_response.status_code, 200)
        self.assertContains(chat_response, "Hello User A")
        
        # Unread count should go back to 0
        response = self.client.get(reverse('chat_dashboard'))
        self.assertEqual(response.context['total_unread_messages'], 0)

    def test_post_direct_message(self):
        self.client.login(username='usera', password='Password123')
        response = self.client.post(
            reverse('send_direct_message', args=[self.user_b.id]),
            {'content': 'Test DM response'}
        )
        self.assertRedirects(response, reverse('direct_chat', args=[self.user_b.id]))
        self.assertTrue(Message.objects.filter(sender=self.user_a, recipient=self.user_b, content='Test DM response').exists())

    def test_event_chat_message(self):
        self.client.login(username='usera', password='Password123')
        response = self.client.post(
            reverse('send_event_message', args=[self.event.id]),
            {'content': 'Hello event group'}
        )
        self.assertRedirects(response, reverse('event_chat', args=[self.event.id]))
        self.assertTrue(Message.objects.filter(sender=self.user_a, event=self.event, content='Hello event group').exists())

    def test_message_validation_both_recipient_and_event_set(self):
        from django.core.exceptions import ValidationError
        msg = Message(sender=self.user_a, recipient=self.user_b, event=self.event, content="Invalid")
        with self.assertRaises(ValidationError):
            msg.full_clean()

    def test_message_validation_neither_recipient_nor_event_set(self):
        from django.core.exceptions import ValidationError
        msg = Message(sender=self.user_a, content="Invalid")
        with self.assertRaises(ValidationError):
            msg.full_clean()

    def test_non_member_cannot_access_event_chat(self):
        self.client.login(username='userb', password='Password123')
        # userb is not registered in Member for self.event
        response = self.client.get(reverse('event_chat', args=[self.event.id]))
        self.assertEqual(response.status_code, 403)

        # Sending message should also fail with 403
        response = self.client.post(
            reverse('send_event_message', args=[self.event.id]),
            {'content': 'Unauthorized'}
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_event_chat_even_if_not_member(self):
        admin_user = self.User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Password123'
        )
        self.client.login(username='admin', password='Password123')
        response = self.client.get(reverse('event_chat', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)


from .models import Venue, Resource, ResourceAllocation, Sponsor
from .forms import EventForm, ResourceAllocationForm

class VenueAndEventBookingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Testing",
            code="CAT-TEST",
            description="Testing category",
            priority="Medium",
            status="Active"
        )
        self.venue = Venue.objects.create(
            name="Main Hall",
            capacity=100,
            location="Building A"
        )
        # Event 1: Aug 10, 2026, 10:00 to 12:00
        self.event1 = Event.objects.create(
            name="Event 1",
            category=self.category,
            venue=self.venue,
            start_date="2026-08-10",
            end_date="2026-08-10",
            start_time="10:00:00",
            end_time="12:00:00",
            max_participants=50,
            registration_deadline="2026-08-09",
            status="Active"
        )

    def test_double_booking_prevention_same_time(self):
        # Event 2 at the same venue, same date, overlapping time (11:00 to 13:00)
        form = EventForm(data={
            'name': 'Overlapping Event',
            'category': self.category.id,
            'venue': self.venue.id,
            'start_date': '2026-08-10',
            'end_date': '2026-08-10',
            'start_time': '11:00:00',
            'end_time': '13:00:00',
            'max_participants': 50,
            'registration_deadline': '2026-08-09',
            'description': 'Overlapping time test',
            'status': 'Active'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertTrue(any("conflict" in err for err in form.errors['__all__']))

    def test_booking_same_venue_different_time_succeeds(self):
        # Event 3 at the same venue, same date, but non-overlapping time (13:00 to 15:00)
        form = EventForm(data={
            'name': 'Non-Overlapping Event',
            'category': self.category.id,
            'venue': self.venue.id,
            'start_date': '2026-08-10',
            'end_date': '2026-08-10',
            'start_time': '13:00:00',
            'end_time': '15:00:00',
            'max_participants': 50,
            'registration_deadline': '2026-08-09',
            'description': 'Non-overlapping time test',
            'status': 'Active'
        })
        self.assertTrue(form.is_valid())


class ResourceAllocationValidationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Testing",
            code="CAT-TEST",
            description="Testing category",
            priority="Medium",
            status="Active"
        )
        self.venue = Venue.objects.create(
            name="Main Hall",
            capacity=100,
            location="Building A"
        )
        # Event 1: Aug 10, 2026, 10:00 to 12:00
        self.event = Event.objects.create(
            name="Event A",
            category=self.category,
            venue=self.venue,
            start_date="2026-08-10",
            end_date="2026-08-10",
            start_time="10:00:00",
            end_time="12:00:00",
            max_participants=50,
            registration_deadline="2026-08-09",
            status="Active"
        )
        self.resource = Resource.objects.create(
            name="Projector",
            resource_type="Equipment",
            total_quantity=5,
            description="High-definition projectors"
        )

    def test_allocation_exceeds_total_inventory_fails(self):
        form = ResourceAllocationForm(data={
            'event': self.event.id,
            'resource': self.resource.id,
            'allocated_quantity': 6
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertTrue(any("Resource conflict" in err for err in form.errors['__all__']))

    def test_allocation_within_inventory_succeeds(self):
        form = ResourceAllocationForm(data={
            'event': self.event.id,
            'resource': self.resource.id,
            'allocated_quantity': 3
        })
        self.assertTrue(form.is_valid())


from .models import Attendance
import json

class Phase3TicketAndAttendeeTests(TestCase):
    """Phase 3: Attendee & Ticket Management Platform — comprehensive test suite."""

    def setUp(self):
        self.User = get_user_model()
        self.staff_user = self.User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='Password123',
            is_staff=True
        )
        self.regular_user = self.User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='Password123'
        )
        self.category = Category.objects.create(
            name="General",
            code="CAT-GEN-P3",
            description="General category",
            priority="Medium",
            status="Active"
        )
        self.venue = Venue.objects.create(
            name="Testing Lab",
            capacity=30,
            location="Room 101"
        )
        self.event = Event.objects.create(
            name="General Seminar",
            category=self.category,
            venue=self.venue,
            start_date="2026-08-01",
            end_date="2026-08-02",
            start_time="09:00:00",
            end_time="17:00:00",
            max_participants=3,
            registration_deadline="2026-07-31",
            status="Active",
            waiting_list_enabled=True
        )

    def _create_member(self, name, email, status='Active', event=None):
        return Member.objects.create(
            name=name,
            email=email,
            phone="1234567890",
            department="CS",
            year="1st",
            event=event or self.event,
            role="Participant",
            status=status
        )

    # ── Model Tests ──────────────────────────────────────────────────────

    def test_member_uuid_auto_generated(self):
        member = self._create_member("UUID Tester", "uuid@example.com")
        self.assertIsNotNone(member.uuid)

    def test_ticket_uuid_and_number_auto_generated(self):
        member = self._create_member("Ticket Gen", "ticketgen@example.com")
        ticket = Ticket.objects.create(member=member, event=self.event)
        self.assertIsNotNone(ticket.uuid)
        self.assertIsNotNone(ticket.ticket_number)
        self.assertTrue(ticket.ticket_number.startswith("TKT-"))

    def test_ticket_default_status_is_active(self):
        member = self._create_member("Status Tester", "status@example.com")
        ticket = Ticket.objects.create(member=member, event=self.event)
        self.assertEqual(ticket.status, Ticket.TicketStatus.ACTIVE)

    def test_multiple_tickets_per_member_allowed(self):
        """Phase 3 switched from OneToOneField to ForeignKey — multiple tickets per member."""
        member = self._create_member("Multi Ticket", "multi@example.com")
        t1 = Ticket.objects.create(member=member, event=self.event)
        t2 = Ticket.objects.create(member=member, event=self.event)
        self.assertEqual(member.tickets.count(), 2)
        self.assertNotEqual(t1.ticket_number, t2.ticket_number)

    def test_attendance_default_status_present(self):
        member = self._create_member("Attendance Tester", "att@example.com")
        record = Attendance.objects.create(
            event=self.event,
            member=member,
            verified_by=self.staff_user
        )
        self.assertEqual(record.status, Attendance.AttendanceStatus.PRESENT)

    # ── Waitlist Capacity & Auto-Promotion Tests ─────────────────────────

    def test_capacity_full_triggers_pending_status(self):
        """When max_participants (3) are filled, new members should be 'Pending'."""
        self._create_member("Member 1", "m1@example.com", status="Active")
        self._create_member("Member 2", "m2@example.com", status="Active")
        self._create_member("Member 3", "m3@example.com", status="Active")
        # 4th member should be waitlisted
        waitlisted = self._create_member("Member 4", "m4@example.com", status="Pending")
        self.assertEqual(waitlisted.status, "Pending")
        # Active count should be 3
        active_count = Member.objects.filter(event=self.event, status='Active').count()
        self.assertEqual(active_count, 3)

    def test_promote_waiting_list_fills_open_seat(self):
        """Deleting an active member should promote the oldest waitlisted member."""
        from event.views import promote_waiting_list

        m1 = self._create_member("Active 1", "active1@example.com", status="Active")
        m2 = self._create_member("Active 2", "active2@example.com", status="Active")
        m3 = self._create_member("Active 3", "active3@example.com", status="Active")
        waiter = self._create_member("Waiting 1", "wait1@example.com", status="Pending")

        # Remove active member
        m1.delete()
        # Promote from waitlist
        promote_waiting_list(self.event)

        waiter.refresh_from_db()
        self.assertEqual(waiter.status, "Active")
        # Should also have a ticket
        self.assertTrue(waiter.tickets.exists())

    # ── Check-in API Tests ───────────────────────────────────────────────

    def test_checkin_api_unauthenticated_redirects(self):
        response = self.client.post(
            reverse('api_checkin'),
            data=json.dumps({'uuid': 'anything'}),
            content_type='application/json'
        )
        # Redirect to login
        self.assertEqual(response.status_code, 302)

    def test_checkin_api_non_staff_forbidden(self):
        self.client.login(username='regularuser', password='Password123')
        response = self.client.post(
            reverse('api_checkin'),
            data=json.dumps({'uuid': 'anything'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_checkin_api_missing_uuid_returns_400(self):
        self.client.login(username='staffuser', password='Password123')
        response = self.client.post(
            reverse('api_checkin'),
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_checkin_api_invalid_uuid_returns_404(self):
        self.client.login(username='staffuser', password='Password123')
        response = self.client.post(
            reverse('api_checkin'),
            data=json.dumps({'uuid': '00000000-0000-0000-0000-000000000000'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)

    def test_checkin_api_success_flow(self):
        member = self._create_member("Checkin User", "checkin@example.com")
        ticket = Ticket.objects.create(member=member, event=self.event)
        self.client.login(username='staffuser', password='Password123')

        response = self.client.post(
            reverse('api_checkin'),
            data=json.dumps({'uuid': str(ticket.uuid)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['member_name'], 'Checkin User')

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.TicketStatus.USED)

        # Attendance record should exist
        self.assertTrue(Attendance.objects.filter(member=member, event=self.event).exists())

    def test_checkin_api_duplicate_scan_rejected(self):
        member = self._create_member("Dupe Scan", "dupe@example.com")
        ticket = Ticket.objects.create(member=member, event=self.event, status=Ticket.TicketStatus.USED)
        self.client.login(username='staffuser', password='Password123')

        response = self.client.post(
            reverse('api_checkin'),
            data=json.dumps({'uuid': str(ticket.uuid)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('already used', response.json().get('message', '').lower())

    def test_checkin_api_cancelled_ticket_rejected(self):
        member = self._create_member("Cancelled", "cancelled@example.com")
        ticket = Ticket.objects.create(member=member, event=self.event, status=Ticket.TicketStatus.CANCELLED)
        self.client.login(username='staffuser', password='Password123')

        response = self.client.post(
            reverse('api_checkin'),
            data=json.dumps({'uuid': str(ticket.uuid)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    # ── Role-based Permission Tests ──────────────────────────────────────

    def test_ticket_list_requires_staff(self):
        self.client.login(username='regularuser', password='Password123')
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 403)

    def test_ticket_list_accessible_by_staff(self):
        self.client.login(username='staffuser', password='Password123')
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 200)

    def test_ticket_details_owner_can_view(self):
        member = self._create_member("Owner", "owner@example.com")
        member.user = self.regular_user
        member.save()
        ticket = Ticket.objects.create(member=member, event=self.event)

        self.client.login(username='regularuser', password='Password123')
        response = self.client.get(reverse('ticket_details', args=[ticket.uuid]))
        self.assertEqual(response.status_code, 200)

    def test_ticket_details_unauthorized_forbidden(self):
        other_user = self.User.objects.create_user(
            username='otheruser', email='other@example.com', password='Password123'
        )
        member = self._create_member("Stranger", "stranger@example.com")
        member.user = other_user
        member.save()
        ticket = Ticket.objects.create(member=member, event=self.event)

        self.client.login(username='regularuser', password='Password123')
        response = self.client.get(reverse('ticket_details', args=[ticket.uuid]))
        self.assertEqual(response.status_code, 403)

    def test_qr_scanner_requires_staff(self):
        self.client.login(username='regularuser', password='Password123')
        response = self.client.get(reverse('qr_scanner'))
        self.assertEqual(response.status_code, 403)

    def test_qr_checkin_allows_organizer_role(self):
        member = self._create_member("Organizer Member", "organizer-member@example.com")
        ticket = Ticket.objects.create(member=member, event=self.event)

        organizer = self.User.objects.create_user(
            username='organizeruser',
            email='organizer@example.com',
            password='Password123'
        )
        UserProfile.objects.update_or_create(user=organizer, defaults={'role': 'organizer'})

        self.client.login(username='organizeruser', password='Password123')
        response = self.client.post(
            reverse('api_checkin'),
            data=json.dumps({'uuid': str(ticket.uuid)}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')

    def test_attendance_list_requires_staff(self):
        self.client.login(username='regularuser', password='Password123')
        response = self.client.get(reverse('attendance_list'))
        self.assertEqual(response.status_code, 403)

    def test_waiting_list_requires_staff(self):
        self.client.login(username='regularuser', password='Password123')
        response = self.client.get(reverse('event_waiting_list', args=[self.event.id]))
        self.assertEqual(response.status_code, 403)

    def test_waiting_list_accessible_by_staff(self):
        self.client.login(username='staffuser', password='Password123')
        response = self.client.get(reverse('event_waiting_list', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)

    # ── Registration Success View ────────────────────────────────────────

    def test_registration_success_view(self):
        member = self._create_member("Success Viewer", "success@example.com")
        member.user = self.regular_user
        member.save()
        ticket = Ticket.objects.create(member=member, event=self.event)

        self.client.login(username='regularuser', password='Password123')
        response = self.client.get(reverse('registration_success', args=[ticket.uuid]))
        self.assertEqual(response.status_code, 200)

    # ── API Endpoint Tests ───────────────────────────────────────────────

    def test_api_register_list_returns_json(self):
        self.client.login(username='staffuser', password='Password123')
        response = self.client.get(reverse('api_register_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_attendance_log_returns_json(self):
        self.client.login(username='staffuser', password='Password123')
        response = self.client.get(reverse('api_attendance_log'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')


from .forms import VendorForm, ContractForm

class VendorAndContractValidationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Testing",
            code="CAT-TEST",
            status="Active"
        )
        self.venue = Venue.objects.create(
            name="Room 202",
            capacity=50,
            location="Block C"
        )
        self.event = Event.objects.create(
            name="Catering Event",
            category=self.category,
            venue=self.venue,
            start_date="2026-08-10",
            end_date="2026-08-11",
            start_time="10:00:00",
            end_time="18:00:00",
            max_participants=100,
            registration_deadline="2026-08-09",
            status="Active"
        )
        self.vendor = Vendor.objects.create(
            name="Fast Food Inc",
            service_category="Catering",
            contact_person="Ravi",
            email="ravi@fastfood.com",
            phone="9876543210",
            rating=4
        )

    def test_vendor_invalid_rating_fails(self):
        form = VendorForm(data={
            'name': 'Test Vendor',
            'service_category': 'Audio',
            'contact_person': 'Mike',
            'email': 'mike@sound.com',
            'phone': '1234567890',
            'rating': 6
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)

    def test_contract_invalid_dates_fails(self):
        form = ContractForm(data={
            'vendor': self.vendor.id,
            'event': self.event.id,
            'contract_amount': 2500.00,
            'status': 'Pending',
            'start_date': '2026-08-12',
            'end_date': '2026-08-10',
            'terms': 'Overdue start test'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertTrue(any("end date cannot be before" in err for err in form.errors['__all__']))


from unittest.mock import patch
from .models import Budget, Expense
from .forms import BudgetForm, ExpenseForm

class BudgetAndExpenseTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Finance", code="FIN-CAT", status="Active")
        self.venue = Venue.objects.create(name="Main Conference Hall", capacity=100, location="Building A")
        self.event = Event.objects.create(
            name="Tech Summit",
            category=self.category,
            venue=self.venue,
            start_date="2026-09-01",
            end_date="2026-09-03",
            start_time="09:00:00",
            end_time="17:00:00",
            max_participants=200,
            registration_deadline="2026-08-31",
            status="Active"
        )
        self.budget = Budget.objects.create(event=self.event, total_amount=1000.00)

    def test_expense_under_budget_succeeds(self):
        form = ExpenseForm(data={
            'budget': self.budget.id,
            'name': 'Catering Expense',
            'amount': 600.00,
            'category': 'Catering',
            'approved': True
        })
        self.assertTrue(form.is_valid())

    def test_expense_over_budget_fails(self):
        Expense.objects.create(budget=self.budget, name='Catering 1', amount=800.00, category='Catering', approved=True)
        form = ExpenseForm(data={
            'budget': self.budget.id,
            'name': 'AV Rentals',
            'amount': 300.00,
            'category': 'AV',
            'approved': True
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertTrue(any("Budget Exceeded" in err for err in form.errors['__all__']))


class RestApiEndpointTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.staff_user = self.User.objects.create_user(username='apistaff', email='apistaff@example.com', password='Password123', is_staff=True)
        self.regular_user = self.User.objects.create_user(username='apiregular', email='apireg@example.com', password='Password123')
        self.category = Category.objects.create(name="API Category", code="CAT-API", status="Active")
        self.venue = Venue.objects.create(name="Auditorium", capacity=150, location="Admin Block")
        self.event = Event.objects.create(
            name="API Showcase",
            category=self.category,
            venue=self.venue,
            start_date="2026-10-01",
            end_date="2026-10-02",
            start_time="10:00:00",
            end_time="16:00:00",
            max_participants=80,
            registration_deadline="2026-09-30",
            status="Active"
        )

    def test_api_read_requires_authentication(self):
        response = self.client.get(reverse('api_event-list'))
        self.assertEqual(response.status_code, 403)

    def test_api_read_succeeds_for_regular_user(self):
        self.client.login(username='apiregular', password='Password123')
        response = self.client.get(reverse('api_event-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.json(), list))

    def test_api_write_requires_staff_user(self):
        self.client.login(username='apiregular', password='Password123')
        response = self.client.post(reverse('api_event-list'), {
            'name': 'API Post Event',
            'category': self.category.id,
            'venue': self.venue.id,
            'start_date': '2026-10-05',
            'end_date': '2026-10-06',
            'start_time': '09:00:00',
            'end_time': '18:00:00',
            'max_participants': 20,
            'registration_deadline': '2026-10-04'
        })
        self.assertEqual(response.status_code, 403)

    def test_api_write_succeeds_for_staff_user(self):
        self.client.login(username='apistaff', password='Password123')
        response = self.client.post(reverse('api_event-list'), {
            'name': 'API Post Event',
            'category': self.category.id,
            'venue': self.venue.id,
            'start_date': '2026-10-05',
            'end_date': '2026-10-06',
            'start_time': '09:00:00',
            'end_time': '18:00:00',
            'max_participants': 20,
            'registration_deadline': '2026-10-04',
            'description': 'This is a test event description',
            'status': 'Active'
        })
        self.assertEqual(response.status_code, 201)


class CeleryTaskTests(TestCase):
    @patch('event.tasks.send_mail')
    def test_send_registration_email_task(self, mock_send_mail):
        category = Category.objects.create(name="Testing", code="CAT-T", status="Active")
        venue = Venue.objects.create(name="Lab", capacity=10, location="Base")
        event = Event.objects.create(
            name="Celery Seminar", category=category, venue=venue,
            start_date="2026-08-01", end_date="2026-08-02",
            start_time="09:00:00", end_time="17:00:00",
            max_participants=10, registration_deadline="2026-07-31",
            status="Active"
        )
        member = Member.objects.create(
            name="Celery User", email="celery@example.com", phone="123456",
            department="IT", year="2nd", event=event, role="Participant",
            status="Active"
        )
        from .tasks import send_registration_email
        send_registration_email(member.id)
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        self.assertEqual(kwargs['recipient_list'], ['celery@example.com'])
        self.assertIn('Registration Confirmed', kwargs['subject'])


class Phase2EventIntelligenceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username='staff_test', email='staff@test.com', password='Password123', is_staff=True
        )
        self.regular_user = user_model.objects.create_user(
            username='regular_test', email='regular@test.com', password='Password123'
        )
        self.category = Category.objects.create(
            name="Technology Events", code="CAT-TECH", priority="High", status="Active"
        )
        self.venue = Venue.objects.create(
            name="Innovation Lab", capacity=50, location="Building A"
        )
        self.event = Event.objects.create(
            name="Quantum Computing Seminar",
            category=self.category,
            venue=self.venue,
            start_date="2026-09-10",
            end_date="2026-09-12",
            start_time="10:00:00",
            end_time="16:00:00",
            max_participants=40,
            registration_deadline="2026-09-08",
            description="Short summary",
            full_description="# Detailed Markdown Guide",
            status=Event.EventStatus.ACTIVE,
            visibility=Event.Visibility.PUBLIC
        )

    def test_base_model_timestamps(self):
        # Category inherits BaseModel
        self.assertIsNotNone(self.category.created_at)
        self.assertIsNotNone(self.category.updated_at)
        self.assertTrue(self.category.is_active)

    def test_duplicate_event_view(self):
        self.client.login(username='staff_test', password='Password123')
        # Create a member to ensure members are NOT duplicated
        Member.objects.create(
            name="Attendee 1", email="attendee@example.com", phone="123456",
            department="CS", year="3rd", event=self.event, role="Participant",
            status="Active"
        )
        
        response = self.client.post(reverse('duplicate_event', args=[self.event.id]), follow=True)
        # Duplicate redirects to edit_event page
        self.assertEqual(response.status_code, 200)
        
        # Verify duplicated event parameters
        duplicated_event = Event.objects.filter(name="Copy of Quantum Computing Seminar").first()
        self.assertIsNotNone(duplicated_event)
        self.assertEqual(duplicated_event.status, Event.EventStatus.PENDING)
        self.assertEqual(duplicated_event.category, self.event.category)
        self.assertEqual(duplicated_event.venue, self.event.venue)
        self.assertEqual(duplicated_event.max_participants, self.event.max_participants)
        self.assertEqual(duplicated_event.full_description, self.event.full_description)
        # Confirm registrations are NOT copied
        self.assertEqual(duplicated_event.members.count(), 0)

    def test_calendar_api_range_filtering(self):
        self.client.login(username='regular_test', password='Password123')
        # API Query matching range
        url = reverse('events_calendar_api') + "?start=2026-09-01T00:00:00&end=2026-09-30T00:00:00"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], "Quantum Computing Seminar")

        # API Query outside range
        url_outside = reverse('events_calendar_api') + "?start=2026-10-01T00:00:00&end=2026-10-31T00:00:00"
        response_outside = self.client.get(url_outside)
        self.assertEqual(response_outside.status_code, 200)
        data_outside = response_outside.json()
        self.assertEqual(len(data_outside), 0)

    def test_private_visibility_clearance(self):
        # Make event private
        self.event.visibility = Event.Visibility.PRIVATE
        self.event.save()

        # Regular user should get PermissionDenied (403)
        self.client.login(username='regular_test', password='Password123')
        response = self.client.get(reverse('event_details', args=[self.event.id]))
        self.assertEqual(response.status_code, 403)

        # Staff user should bypass visibility controls
        self.client.login(username='staff_test', password='Password123')
        response_staff = self.client.get(reverse('event_details', args=[self.event.id]))
        self.assertEqual(response_staff.status_code, 200)


from .models import Announcement

class AnnouncementTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.staff_user = self.user_model.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='Password123',
            is_staff=True
        )
        self.regular_user = self.user_model.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='Password123'
        )
        self.announcement = Announcement.objects.create(
            title="System Maintenance",
            content="We will have system maintenance tonight.",
            audience="all",
            created_by=self.staff_user
        )

    def test_announcement_list_resolves_and_renders(self):
        self.client.login(username='regular_user', password='Password123')
        response = self.client.get(reverse('announcement_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Maintenance")

    def test_announcement_details_resolves_and_renders(self):
        self.client.login(username='regular_user', password='Password123')
        response = self.client.get(reverse('announcement_details', args=[self.announcement.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We will have system maintenance tonight.")

    def test_staff_user_can_create_announcement(self):
        self.client.login(username='staff_user', password='Password123')
        response = self.client.post(reverse('create_announcement'), {
            'title': 'New Event Notification',
            'content': 'Check out the new coding event.',
            'audience': 'all'
        })
        self.assertEqual(response.status_code, 302) # Redirect to list
        self.assertTrue(Announcement.objects.filter(title='New Event Notification').exists())

    def test_regular_user_cannot_create_announcement(self):
        self.client.login(username='regular_user', password='Password123')
        response = self.client.post(reverse('create_announcement'), {
            'title': 'Hack Attempt',
            'content': 'Attempt to broadcast spam.',
            'audience': 'all'
        })
        self.assertEqual(response.status_code, 403) # Forbidden
        self.assertFalse(Announcement.objects.filter(title='Hack Attempt').exists())

    def test_staff_user_can_unarchive_announcement(self):
        self.announcement.is_active = False
        self.announcement.save()
        self.client.login(username='staff_user', password='Password123')
        response = self.client.post(reverse('unarchive_announcement', args=[self.announcement.id]))
        self.assertEqual(response.status_code, 302) # Redirect to details
        self.announcement.refresh_from_db()
        self.assertTrue(self.announcement.is_active)

    def test_regular_user_cannot_unarchive_announcement(self):
        self.announcement.is_active = False
        self.announcement.save()
        self.client.login(username='regular_user', password='Password123')
        response = self.client.post(reverse('unarchive_announcement', args=[self.announcement.id]))
        self.assertEqual(response.status_code, 403) # Forbidden
        self.announcement.refresh_from_db()
        self.assertFalse(self.announcement.is_active)


class TicketCheckinResetTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from event.models import UserProfile, Event, Member, Ticket, Venue, Category

        User = get_user_model()
        
        self.staff_user = User.objects.create_user(username='staff_t', password='Password123', is_staff=True)
        self.regular_user = User.objects.create_user(username='regular_t', password='Password123')
        
        UserProfile.objects.get_or_create(user=self.staff_user, defaults={'role': 'admin'})
        UserProfile.objects.get_or_create(user=self.regular_user, defaults={'role': 'viewer'})
        
        self.category = Category.objects.create(name='Tech Events')
        self.venue = Venue.objects.create(name='Hall A', capacity=100)
        self.event = Event.objects.create(
            name='Tech Summit',
            category=self.category,
            venue=self.venue,
            start_date=timezone.localdate(),
            start_time='09:00:00',
            end_date=timezone.localdate(),
            end_time='17:00:00',
            max_participants=100,
            registration_deadline=timezone.localdate(),
            status='Active'
        )

        
        self.member = Member.objects.create(
            event=self.event,
            user=self.regular_user,
            name='Regular User',
            email='regular@example.com',
            status='Active'
        )
        
        self.ticket = Ticket.objects.create(
            member=self.member,
            event=self.event,
            ticket_number='TKT-TEST-123',
            status=Ticket.TicketStatus.USED
        )

    def test_staff_can_reset_ticket_checkin(self):
        from event.models import Attendance, Ticket
        Attendance.objects.create(
            event=self.event,
            member=self.member,
            check_in_time=timezone.now(),
            status=Attendance.AttendanceStatus.PRESENT
        )
        self.member.check_in_time = timezone.now()
        self.member.save()
        
        self.client.login(username='staff_t', password='Password123')
        response = self.client.post(reverse('reset_ticket_checkin', args=[self.ticket.uuid]))
        self.assertEqual(response.status_code, 302) # Redirect to details
        
        self.ticket.refresh_from_db()
        self.member.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.TicketStatus.ACTIVE)
        self.assertNil = self.assertIsNone(self.member.check_in_time)
        self.assertFalse(Attendance.objects.filter(member=self.member, event=self.event).exists())

    def test_regular_user_cannot_reset_ticket_checkin(self):
        self.client.login(username='regular_t', password='Password123')
        response = self.client.post(reverse('reset_ticket_checkin', args=[self.ticket.uuid]))
        self.assertEqual(response.status_code, 403) # Forbidden







