from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Category, Event, Member, Contact, Venue, Sponsor, Resource, ResourceAllocation, Vendor, Contract, Budget, Expense, UserProfile, Announcement

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'code', 'description', 'image', 'priority', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Technical Events'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CAT-TECH'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Provide a brief explanation of the category...'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'name', 'category', 'venue', 'start_date', 'end_date', 
            'start_time', 'end_time', 'max_participants', 'registration_deadline', 
            'banner', 'description', 'full_description', 'sponsors', 'organizers',
            'operational_requirements', 'status', 'visibility', 'waiting_list_enabled'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Web Dev Hackathon'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'venue': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 100'}),
            'registration_deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'banner': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Provide short summary...'}),
            'full_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Provide full description in Markdown...'}),
            'sponsors': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'organizers': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'operational_requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter operational requirements...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'waiting_list_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        venue = cleaned_data.get('venue')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if venue and start_date and end_date and start_time and end_time:
            overlapping_events = Event.objects.filter(
                venue=venue,
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            if self.instance and self.instance.pk:
                overlapping_events = overlapping_events.exclude(pk=self.instance.pk)

            for event in overlapping_events:
                if (start_time < event.end_time) and (end_time > event.start_time):
                    raise forms.ValidationError(
                        f"Scheduling conflict: Venue '{venue.name}' is already booked for event '{event.name}' "
                        f"on {event.start_date} from {event.start_time} to {event.end_time}."
                    )
        return cleaned_data

class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['name', 'capacity', 'location', 'amenities', 'description', 'status', 'image', 'available_from', 'available_to', 'is_bookable']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main Auditorium'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 500'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Block A, 1st Floor'}),
            'amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'e.g. Projector, Sound System, AC'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide venue description...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'available_from': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'available_to': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_bookable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = ['name', 'logo', 'website', 'contact_person', 'email', 'phone', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Infosys'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'e.g. https://www.infosys.com'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. contact@infosys.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide sponsor summary...'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'phone', 'profile_photo',
            'theme_preference', 'accent_color', 'font', 'border_radius',
            'compact_mode', 'animations_enabled', 'reduced_motion',
            'timezone', 'language', 'notifications_enabled'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tell us about yourself...'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'theme_preference': forms.Select(attrs={'class': 'form-select'}),
            'accent_color': forms.Select(attrs={'class': 'form-select'}),
            'font': forms.Select(attrs={'class': 'form-select'}),
            'border_radius': forms.Select(attrs={'class': 'form-select'}),
            'compact_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'animations_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reduced_motion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. UTC, Asia/Kolkata'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. en, fr'}),
            'notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['name', 'resource_type', 'total_quantity', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wired Microphone'}),
            'resource_type': forms.Select(attrs={'class': 'form-select'}),
            'total_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide resource details...'}),
        }

class ResourceAllocationForm(forms.ModelForm):
    class Meta:
        model = ResourceAllocation
        fields = ['event', 'resource', 'allocated_quantity']
        widgets = {
            'event': forms.Select(attrs={'class': 'form-select'}),
            'resource': forms.Select(attrs={'class': 'form-select'}),
            'allocated_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        resource = cleaned_data.get('resource')
        allocated_quantity = cleaned_data.get('allocated_quantity')
        event = cleaned_data.get('event')

        if resource and allocated_quantity and event:
            if allocated_quantity <= 0:
                raise forms.ValidationError("Allocated quantity must be greater than zero.")
                
            overlapping_events_ids = Event.objects.filter(
                start_date__lte=event.end_date,
                end_date__gte=event.start_date
            ).values_list('id', flat=True)

            active_allocations = ResourceAllocation.objects.filter(
                resource=resource,
                event_id__in=overlapping_events_ids
            )
            if self.instance and self.instance.pk:
                active_allocations = active_allocations.exclude(pk=self.instance.pk)

            from django.db.models import Sum
            total_allocated = active_allocations.aggregate(Sum('allocated_quantity'))['allocated_quantity__sum'] or 0
            
            remaining = resource.total_quantity - total_allocated
            if allocated_quantity > remaining:
                raise forms.ValidationError(
                    f"Resource conflict: Only {remaining} units of '{resource.name}' are available for the event's "
                    f"date period (total {resource.total_quantity}, allocated {total_allocated})."
                )
        return cleaned_data

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'email', 'phone', 'department', 'year', 'event', 'role', 'status', 'organization', 'designation', 'emergency_contact', 'payment_status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Rohan Sharma'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. rohan@college.edu'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +91 98765 11111'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science & Engineering'}),
            'year': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. College / Company Name'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Student / Software Developer'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +91 99999 88888'}),
            'payment_status': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Unpaid'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        year = cleaned_data.get('year')

        if role in ['Participant', 'Volunteer'] and not year:
            self.add_error('year', 'Year of study is required for Participants and Volunteers.')
        elif role == 'Organizer' and year:
            # Clear the year field if role is Organizer
            cleaned_data['year'] = None
            
        return cleaned_data

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Inquiry regarding venue'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Type your message here...'}),
        }

class UserSignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email'].strip().lower()
        if commit:
            user.save()
        return user

class SelfRegistrationForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['phone', 'department', 'year', 'role', 'organization', 'designation', 'emergency_contact']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +91 98765 11111'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science & Engineering'}),
            'year': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. College / Company Name'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Student / Software Developer'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +91 99999 88888'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            ('Participant', 'Participant'),
            ('Volunteer', 'Volunteer'),
        ]

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get('year')
        if not year:
            self.add_error('year', 'Year of study is required for Participants and Volunteers.')
        return cleaned_data


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['name', 'service_category', 'contact_person', 'email', 'phone', 'address', 'rating']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Master Catering Services'}),
            'service_category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Catering'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Jane Doe'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. contact@vendor.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +91 98765 43210'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter vendor address...'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5'}),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is not None and (rating < 0 or rating > 5):
            raise forms.ValidationError("Rating must be between 0 and 5.")
        return rating


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ['vendor', 'event', 'contract_amount', 'status', 'start_date', 'end_date', 'terms', 'signed_document']
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'contract_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5000.00'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter agreement details...'}),
            'signed_document': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Contract end date cannot be before the start date.")
        return cleaned_data


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['event', 'total_amount']
        widgets = {
            'event': forms.Select(attrs={'class': 'form-select'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10000.00'}),
        }

    def clean_total_amount(self):
        total_amount = self.cleaned_data.get('total_amount')
        if total_amount is not None and total_amount <= 0:
            raise forms.ValidationError("Budget total amount must be greater than zero.")
        return total_amount


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['budget', 'name', 'amount', 'category', 'invoice_document', 'approved']
        widgets = {
            'budget': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Stage Decoration Catering'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1500.00'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'invoice_document': forms.FileInput(attrs={'class': 'form-control'}),
            'approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        budget = cleaned_data.get('budget')
        amount = cleaned_data.get('amount')

        if budget and amount:
            if amount <= 0:
                self.add_error('amount', 'Expense amount must be greater than zero.')

            from django.db.models import Sum
            expenses_query = Expense.objects.filter(budget=budget)
            if self.instance and self.instance.pk:
                expenses_query = expenses_query.exclude(pk=self.instance.pk)
            
            existing_spent = expenses_query.aggregate(Sum('amount'))['amount__sum'] or 0
            if existing_spent + amount > budget.total_amount:
                raise forms.ValidationError(
                    f"Budget Exceeded: Remaining budget balance is ${budget.total_amount - existing_spent}, "
                    f"but current expense is ${amount}."
                )
        return cleaned_data


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'event', 'audience']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter announcement title...'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Type announcement content here...'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'audience': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event'].empty_label = "Global (All Users / System-wide)"
        self.fields['event'].required = False


