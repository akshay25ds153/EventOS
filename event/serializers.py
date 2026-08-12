from rest_framework import serializers
from .models import Category, Event, Member, Vendor, Budget, Venue

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

class EventSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    venue_name = serializers.ReadOnlyField(source='venue.name')

    class Meta:
        model = Event
        fields = '__all__'

class MemberSerializer(serializers.ModelSerializer):
    event_name = serializers.ReadOnlyField(source='event.name')

    class Meta:
        model = Member
        fields = '__all__'

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'

class BudgetSerializer(serializers.ModelSerializer):
    event_name = serializers.ReadOnlyField(source='event.name')

    class Meta:
        model = Budget
        fields = '__all__'
