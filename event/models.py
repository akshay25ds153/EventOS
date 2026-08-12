from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from django.utils import timezone


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='%(class)s_updated')
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class UserProfile(models.Model):
    """Extended profile for each Django User."""
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System'),
    ]

    ACCENT_CHOICES = [
        ('indigo', 'Indigo'),
        ('ocean', 'Ocean Blue'),
        ('teal', 'Teal'),
        ('rose', 'Rose'),
        ('violet', 'Violet'),
        ('emerald', 'Emerald'),
    ]

    FONT_CHOICES = [
        ('plus-jakarta', 'Plus Jakarta Sans'),
        ('inter', 'Inter'),
        ('poppins', 'Poppins'),
        ('outfit', 'Outfit'),
    ]

    BORDER_RADIUS_CHOICES = [
        ('sharp', 'Sharp (0px)'),
        ('rounded', 'Rounded (8px)'),
        ('extra-rounded', 'Extra Rounded (16px)'),
    ]

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('organizer', 'Organizer'),
        ('volunteer', 'Volunteer'),
        ('viewer', 'Viewer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    bio = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')

    # Roles & Styling preferences
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    theme_preference = models.CharField(max_length=15, choices=THEME_CHOICES, default='light')
    accent_color = models.CharField(max_length=20, choices=ACCENT_CHOICES, default='indigo')
    font = models.CharField(max_length=50, choices=FONT_CHOICES, default='plus-jakarta')
    border_radius = models.CharField(max_length=20, choices=BORDER_RADIUS_CHOICES, default='rounded')
    compact_mode = models.BooleanField(default=False)
    animations_enabled = models.BooleanField(default=True)
    reduced_motion = models.BooleanField(default=False)

    # Analytics, localization & notifications
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    notifications_enabled = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def photo_url(self):
        if self.profile_photo and hasattr(self.profile_photo, 'url'):
            return self.profile_photo.url
        return None


@receiver(post_save, sender=User)
def create_or_save_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)

class Category(BaseModel):
    PRIORITY_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return self.name

class Venue(BaseModel):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Maintenance', 'Maintenance'),
        ('Inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    location = models.CharField(max_length=200)
    amenities = models.TextField(blank=True)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    image = models.ImageField(upload_to='venue_images/', blank=True, null=True)
    available_from = models.TimeField(null=True, blank=True)
    available_to = models.TimeField(null=True, blank=True)
    is_bookable = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Sponsor(BaseModel):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='sponsor_logos/', blank=True, null=True)
    website = models.URLField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name

class Event(BaseModel):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'

    class EventStatus(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        PENDING = 'Pending', 'Pending'
        COMPLETED = 'Completed', 'Completed'
        CANCELLED = 'Cancelled', 'Cancelled'

    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='events')
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, related_name='events', null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_participants = models.IntegerField()
    registration_deadline = models.DateField()
    banner = models.ImageField(upload_to='event_images/', blank=True, null=True)
    description = models.TextField()
    full_description = models.TextField(blank=True, default='')
    sponsors = models.ManyToManyField(Sponsor, blank=True, related_name='events')
    organizers = models.ManyToManyField(User, blank=True, related_name='organized_events')
    operational_requirements = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=EventStatus.choices, default=EventStatus.PENDING, blank=True)
    visibility = models.CharField(max_length=15, choices=Visibility.choices, default=Visibility.PUBLIC, blank=True)
    waiting_list_enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Member(BaseModel):
    YEAR_CHOICES = [
        ('1st', '1st Year'),
        ('2nd', '2nd Year'),
        ('3rd', '3rd Year'),
        ('4th', '4th Year'),
        ('PG', 'Postgraduate'),
    ]
    ROLE_CHOICES = [
        ('Participant', 'Participant'),
        ('Volunteer', 'Volunteer'),
        ('Organizer', 'Organizer'),
    ]
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Pending', 'Pending'),
        ('Inactive', 'Inactive'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='memberships')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    department = models.CharField(max_length=100)
    year = models.CharField(max_length=10, choices=YEAR_CHOICES, blank=True, null=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Participant')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Active')

    # Extended Phase 3 fields
    registration_number = models.CharField(max_length=50, blank=True, unique=True, null=True)
    uuid = models.UUIDField(unique=True, editable=False, null=True)
    organization = models.CharField(max_length=100, blank=True, default='')
    designation = models.CharField(max_length=100, blank=True, default='')
    emergency_contact = models.CharField(max_length=20, blank=True, default='')
    registration_date = models.DateTimeField(default=timezone.now)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, default='Unpaid', blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = uuid.uuid4()
        super().save(*args, **kwargs)

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='received_messages')
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.recipient and self.event:
            raise ValidationError("A message cannot have both a recipient (DM) and an event (group chat).")
        if not self.recipient and not self.event:
            raise ValidationError("A message must have either a recipient (DM) or an event (group chat).")
            
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.event:
            return f"[{self.event.name}] {self.sender.username}: {self.content[:30]}"
        return f"{self.sender.username} -> {self.recipient.username}: {self.content[:30]}"

class Resource(BaseModel):
    RESOURCE_TYPES = [
        ('Equipment', 'Equipment'),
        ('Transportation', 'Transportation'),
        ('Staff', 'Staff / Volunteer'),
        ('Other', 'Other'),
    ]
    name = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    total_quantity = models.IntegerField(default=1)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.resource_type})"

class ResourceAllocation(BaseModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='resource_allocations')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='allocations')
    allocated_quantity = models.IntegerField(default=1)
    allocated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.allocated_quantity}x {self.resource.name} for {self.event.name}"


class Ticket(BaseModel):
    class TicketStatus(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        USED = 'Used', 'Used'
        CANCELLED = 'Cancelled', 'Cancelled'

    uuid = models.UUIDField(unique=True, editable=False, null=True)
    ticket_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    qr_code = models.ImageField(upload_to='ticket_qrs/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='ticket_pdfs/', blank=True, null=True)
    issue_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=TicketStatus.choices, default=TicketStatus.ACTIVE)

    def __str__(self):
        return f"Ticket {self.ticket_number} for {self.member.name}"

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = uuid.uuid4()
        if not self.ticket_number:
            self.ticket_number = f"TKT-{str(uuid.uuid4())[:12].upper()}"
        super().save(*args, **kwargs)


class Attendance(BaseModel):
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'Present', 'Present'
        ABSENT = 'Absent', 'Absent'

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendance_records')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='attendance_records')
    check_in_time = models.DateTimeField(default=timezone.now)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_attendances')
    verification_device = models.CharField(max_length=100, blank=True, default='Webcam Scanner')

    def __str__(self):
        return f"{self.member.name} - {self.event.name} ({self.status})"


class Vendor(BaseModel):
    name = models.CharField(max_length=100)
    service_category = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    rating = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.service_category})"


class Contract(BaseModel):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Terminated', 'Terminated'),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='contracts')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='contracts')
    contract_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    start_date = models.DateField()
    end_date = models.DateField()
    terms = models.TextField(blank=True)
    signed_document = models.FileField(upload_to='contracts/', blank=True, null=True)

    def __str__(self):
        return f"Contract with {self.vendor.name} for {self.event.name} (${self.contract_amount})"


class Budget(BaseModel):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='budget')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Budget for {self.event.name} (${self.total_amount})"


class Expense(BaseModel):
    CATEGORY_CHOICES = [
        ('Catering', 'Catering'),
        ('AV', 'Audio / Visual'),
        ('Decoration', 'Decoration'),
        ('Marketing', 'Marketing'),
        ('Others', 'Others'),
    ]

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='expenses')
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Others')
    invoice_document = models.FileField(upload_to='invoices/', blank=True, null=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - ${self.amount} ({self.category})"


class EventImage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='event_gallery/')
    caption = models.CharField(max_length=200, blank=True, default='')
    order = models.IntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"Image for {self.event.name} (order: {self.order})"


class EventAttachment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='event_attachments/')
    name = models.CharField(max_length=100)
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment {self.name} for {self.event.name}"


class Announcement(BaseModel):
    AUDIENCE_CHOICES = [
        ('all', 'All Users'),
        ('admin', 'Admin Only'),
        ('organizer', 'Organizer Only'),
        ('volunteer', 'Volunteer Only'),
        ('viewer', 'Viewer/Student Only'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')

    def __str__(self):
        return self.title

