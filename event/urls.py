from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

router = DefaultRouter()
router.register(r'api/categories', api_views.CategoryViewSet, basename='api_category')
router.register(r'api/venues', api_views.VenueViewSet, basename='api_venue')
router.register(r'api/events', api_views.EventViewSet, basename='api_event')
router.register(r'api/members', api_views.MemberViewSet, basename='api_member')
router.register(r'api/vendors', api_views.VendorViewSet, basename='api_vendor')
router.register(r'api/budgets', api_views.BudgetViewSet, basename='api_budget')

urlpatterns = [
    # Public Pages
    path('', views.landing_page, name='landing'),
    path('contact/', views.contact_view, name='contact'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='authentication/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='authentication/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='authentication/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='authentication/password_reset_complete.html'), name='password_reset_complete'),
    
    # Admin Panel (Protected)
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Category CRUD
    path('category/', views.category_list, name='category_list'),
    path('category/create/', views.create_category, name='create_category'),
    path('category/<int:pk>/', views.category_details, name='category_details'),
    path('category/<int:pk>/edit/', views.edit_category, name='edit_category'),
    path('category/<int:pk>/delete/', views.delete_category, name='delete_category'),
    
    # Announcement CRUD
    path('announcement/', views.announcement_list, name='announcement_list'),
    path('announcement/create/', views.create_announcement, name='create_announcement'),
    path('announcement/<int:pk>/', views.announcement_details, name='announcement_details'),
    path('announcement/<int:pk>/edit/', views.edit_announcement, name='edit_announcement'),
    path('announcement/<int:pk>/delete/', views.delete_announcement, name='delete_announcement'),
    path('announcement/<int:pk>/unarchive/', views.unarchive_announcement, name='unarchive_announcement'),


    
    # Event CRUD
    path('event/', views.event_list, name='event_list'),
    path('event/create/', views.create_event, name='create_event'),
    path('event/calendar/', views.event_calendar, name='event_calendar'),
    path('api/events/calendar/', views.events_calendar_api, name='events_calendar_api'),
    path('event/<int:pk>/', views.event_details, name='event_details'),
    path('event/<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('event/<int:pk>/delete/', views.delete_event, name='delete_event'),
    path('event/<int:pk>/duplicate/', views.duplicate_event, name='duplicate_event'),
    path('event/<int:pk>/register/', views.event_self_register, name='event_self_register'),
    
    # Member CRUD
    path('member/', views.member_list, name='member_list'),
    path('member/add/', views.add_member, name='add_member'),
    path('member/add-event-member/', views.add_member, name='add_event_member'),
    path('member/<int:pk>/', views.member_details, name='member_details'),
    path('member/<int:pk>/edit/', views.edit_member, name='edit_member'),
    path('member/<int:pk>/delete/', views.delete_member, name='delete_member'),
    path('joined-events/', views.joined_events, name='joined_events'),
    
    # Reports
    path('completed-events/', views.completed_events, name='completed_events'),
    
    # Venue CRUD
    path('venue/', views.venue_list, name='venue_list'),
    path('venue/create/', views.create_venue, name='create_venue'),
    path('venue/<int:pk>/', views.venue_details, name='venue_details'),
    path('venue/<int:pk>/edit/', views.edit_venue, name='edit_venue'),
    path('venue/<int:pk>/delete/', views.delete_venue, name='delete_venue'),
    
    # Resource CRUD & Allocation
    path('resource/', views.resource_list, name='resource_list'),
    path('resource/create/', views.create_resource, name='create_resource'),
    path('resource/<int:pk>/edit/', views.edit_resource, name='edit_resource'),
    path('resource/<int:pk>/delete/', views.delete_resource, name='delete_resource'),
    path('resource/allocate/', views.allocate_resource, name='allocate_resource'),
    path('resource/allocation/<int:pk>/delete/', views.delete_allocation, name='delete_allocation'),

    # Sponsor CRUD
    path('sponsor/', views.sponsor_list, name='sponsor_list'),
    path('sponsor/create/', views.create_sponsor, name='create_sponsor'),
    path('sponsor/<int:pk>/edit/', views.edit_sponsor, name='edit_sponsor'),
    path('sponsor/<int:pk>/delete/', views.delete_sponsor, name='delete_sponsor'),

    # Tickets & Check-In
    path('registration-success/<uuid:ticket_uuid>/', views.registration_success, name='registration_success'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/<uuid:uuid_val>/', views.ticket_details, name='ticket_details'),
    path('tickets/<uuid:uuid_val>/pdf/', views.download_ticket_pdf, name='download_ticket_pdf'),
    path('tickets/<uuid:uuid_val>/reset/', views.reset_ticket_checkin, name='reset_ticket_checkin'),

    path('attendance/', views.attendance_list, name='attendance_list'),
    path('qr-scanner/', views.qr_scanner_view, name='qr_scanner'),
    path('event/<int:pk>/waiting-list/', views.event_waiting_list, name='event_waiting_list'),
    path('api/register/', views.api_register_list, name='api_register_list'),
    path('api/checkin/', views.api_checkin, name='api_checkin'),
    path('api/attendance/', views.api_attendance_log, name='api_attendance_log'),

    # Vendor CRUD
    path('vendor/', views.vendor_list, name='vendor_list'),
    path('vendor/create/', views.create_vendor, name='create_vendor'),
    path('vendor/<int:pk>/edit/', views.edit_vendor, name='edit_vendor'),
    path('vendor/<int:pk>/delete/', views.delete_vendor, name='delete_vendor'),

    # Contract CRUD
    path('contract/', views.contract_list, name='contract_list'),
    path('contract/create/', views.create_contract, name='create_contract'),
    path('contract/<int:pk>/edit/', views.edit_contract, name='edit_contract'),
    path('contract/<int:pk>/delete/', views.delete_contract, name='delete_contract'),

    # Budget & Expenses
    path('budget/', views.budget_list, name='budget_list'),
    path('budget/create/', views.create_budget, name='create_budget'),
    path('budget/<int:pk>/', views.budget_details, name='budget_details'),
    path('budget/<int:pk>/delete/', views.delete_budget, name='delete_budget'),
    path('expense/create/', views.create_expense, name='create_expense'),
    path('expense/<int:pk>/approve/', views.approve_expense, name='approve_expense'),
    path('expense/<int:pk>/delete/', views.delete_expense, name='delete_expense'),
    
    # Messaging
    path('messages/', views.chat_dashboard, name='chat_dashboard'),
    path('messages/direct/<int:user_id>/', views.direct_chat_view, name='direct_chat'),
    path('messages/direct/<int:user_id>/send/', views.send_direct_message, name='send_direct_message'),
    path('events/<int:event_id>/chat/', views.event_chat_view, name='event_chat'),
    path('events/<int:event_id>/chat/send/', views.send_event_message, name='send_event_message'),
    path('messages/mark-read/<int:user_id>/', views.mark_messages_read, name='mark_messages_read'),
    # Global Search API
    path('search/', views.global_search, name='global_search'),
    # Profile Preferences API
    path('api/profile/preferences/', views.update_preferences_api, name='update_preferences_api'),
    path('', include(router.urls)),
]
