from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import migrations

CATEGORIES = [
    (1, 'main', 'Main'),
    (2, 'dessert', 'Dessert'),
    (3, 'drinks', 'Drinks'),
]

MENU_ITEMS = [
    (1, 'Beef Pasta', '12.00', 1, True),
    (2, 'Tomato Pasta', '5.00', 1, False),
    (3, 'Grilled Fish', '15.00', 1, False),
    (4, 'Chocolate Cake', '6.50', 2, False),
    (5, 'Ice Cream', '4.00', 2, False),
    (6, 'Lemonade', '3.00', 3, False),
]

# username, password, email, group, is_superuser, token
# Tokens are fixed so they always match notes.txt, even after re-running migrate.
USERS = [
    ('admin', 'Admin@12345', 'admin@littlelemon.com', None, True,
     'e9c025a2eaec0ee70c583b707d8ccf32e60cd7db'),
    ('manager1', 'Manager@123', 'manager1@littlelemon.com', 'Manager', False,
     '86fb8ea7454c5165a2f6520b7d1aa7e68e35ea5d'),
    ('delivery1', 'Delivery@123', 'delivery1@littlelemon.com', 'Delivery crew', False,
     '3c9eebc4890312f300166e189104bd7ad99a6f43'),
    ('customer1', 'Customer@123', 'customer1@littlelemon.com', None, False,
     '2d363bbd033a6fa70b351a66d1e749eb003c1e7d'),
    ('customer2', 'Customer@123', 'customer2@littlelemon.com', None, False,
     'b49e114462c97a8204b11636cc7559ffe774f271'),
]


def load_sample_data(apps, schema_editor):
    Category = apps.get_model('LittleLemonAPI', 'Category')
    MenuItem = apps.get_model('LittleLemonAPI', 'MenuItem')
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    Token = apps.get_model('authtoken', 'Token')

    for pk, slug, title in CATEGORIES:
        Category.objects.update_or_create(pk=pk, defaults={'slug': slug, 'title': title})

    for pk, title, price, category_id, featured in MENU_ITEMS:
        MenuItem.objects.update_or_create(
            pk=pk,
            defaults={
                'title': title,
                'price': Decimal(price),
                'category_id': category_id,
                'featured': featured,
            },
        )

    for username, password, email, group_name, superuser, token in USERS:
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                'email': email,
                'password': make_password(password),
                'is_superuser': superuser,
                'is_staff': superuser,
                'is_active': True,
            },
        )
        if group_name:
            user.groups.add(Group.objects.get(name=group_name))
        Token.objects.filter(user=user).delete()
        Token.objects.create(key=token, user=user)


def remove_sample_data(apps, schema_editor):
    apps.get_model('auth', 'User').objects.filter(username__in=[u[0] for u in USERS]).delete()
    apps.get_model('LittleLemonAPI', 'MenuItem').objects.filter(pk__in=[m[0] for m in MENU_ITEMS]).delete()
    apps.get_model('LittleLemonAPI', 'Category').objects.filter(pk__in=[c[0] for c in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('LittleLemonAPI', '0002_create_groups'),
        ('authtoken', '0004_alter_tokenproxy_options'),
    ]

    operations = [
        migrations.RunPython(load_sample_data, remove_sample_data),
    ]
