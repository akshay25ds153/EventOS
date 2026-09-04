from django.db import migrations


def seed_event_options(apps, schema_editor):
    Category = apps.get_model('event', 'Category')
    Venue = apps.get_model('event', 'Venue')

    if not Category.objects.exists():
        Category.objects.create(
            name='General Events',
            code='CAT-GEN',
            description='General college events and activities.',
            priority='Medium',
            status='Active',
        )

    if not Venue.objects.exists():
        Venue.objects.create(
            name='Main Auditorium',
            capacity=500,
            location='Main Campus',
            description='Primary venue for college events.',
            status='Active',
            is_bookable=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('event', '0015_announcement'),
    ]

    operations = [
        migrations.RunPython(seed_event_options, migrations.RunPython.noop),
    ]
