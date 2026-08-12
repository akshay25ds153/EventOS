from django.db.models import Q
from .models import Message, UserProfile, Announcement, Member

def announcements_processor(request):
    if request.user.is_authenticated:
        role = getattr(request.user, 'profile', None).role if hasattr(request.user, 'profile') else 'viewer'
        
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
        ).order_by('-created_at')[:5]
        
        return {
            'global_announcements': announcements,
            'global_announcements_count': len(announcements),
        }
    return {
        'global_announcements': [],
        'global_announcements_count': 0,
    }


def unread_messages_processor(request):
    if request.user.is_authenticated:
        total_unread = Message.objects.filter(recipient=request.user, is_read=False).count()
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return {
            'total_unread_messages': total_unread,
            'global_user_profile': user_profile,
        }
    return {
        'total_unread_messages': 0,
        'global_user_profile': None,
    }

def user_preferences(request):
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if not profile:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return {
            'user_theme': profile.theme_preference,
            'user_accent': profile.accent_color,
            'user_font': profile.font,
            'user_border_radius': profile.border_radius,
            'user_compact': profile.compact_mode,
            'user_animations': profile.animations_enabled,
            'user_reduced_motion': profile.reduced_motion,
            'user_role': profile.role,
        }
    return {
        'user_theme': 'light',
        'user_accent': 'indigo',
        'user_font': 'plus-jakarta',
        'user_border_radius': 'rounded',
        'user_compact': False,
        'user_animations': True,
        'user_reduced_motion': False,
        'user_role': 'viewer',
    }
