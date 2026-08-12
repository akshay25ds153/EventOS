from rest_framework import viewsets, permissions
from .models import Category, Event, Member, Vendor, Budget, Venue
from .serializers import (
    CategorySerializer, EventSerializer, MemberSerializer, 
    VendorSerializer, BudgetSerializer, VenueSerializer
)

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow staff members to edit objects,
    but allow authenticated users to view them.
    """
    def has_permission(self, request, view):
        # Authenticated users can perform safe reads (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Writing operations require staff status
        return request.user and request.user.is_staff

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all().order_by('name')
    serializer_class = VenueSerializer
    permission_classes = [IsStaffOrReadOnly]

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('-start_date')
    serializer_class = EventSerializer
    permission_classes = [IsStaffOrReadOnly]

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all().order_by('-created_at')
    serializer_class = MemberSerializer
    permission_classes = [IsStaffOrReadOnly]

class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all().order_by('name')
    serializer_class = VendorSerializer
    permission_classes = [IsStaffOrReadOnly]

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all().order_by('-created_at')
    serializer_class = BudgetSerializer
    permission_classes = [IsStaffOrReadOnly]
