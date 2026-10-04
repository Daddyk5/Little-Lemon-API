from rest_framework.permissions import BasePermission

MANAGER_GROUP = 'Manager'
DELIVERY_CREW_GROUP = 'Delivery crew'


def in_group(user, group_name):
    return bool(user and user.is_authenticated and user.groups.filter(name=group_name).exists())


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.is_staff))


def is_manager(user):
    return in_group(user, MANAGER_GROUP)


def is_delivery_crew(user):
    return in_group(user, DELIVERY_CREW_GROUP)


def is_customer(user):
    return bool(
        user
        and user.is_authenticated
        and not user.groups.filter(name__in=[MANAGER_GROUP, DELIVERY_CREW_GROUP]).exists()
    )


class IsManager(BasePermission):
    message = 'Only managers can perform this action.'

    def has_permission(self, request, view):
        return is_manager(request.user)


class IsDeliveryCrew(BasePermission):
    message = 'Only delivery crew can perform this action.'

    def has_permission(self, request, view):
        return is_delivery_crew(request.user)


class IsAdminOrManager(BasePermission):
    message = 'Only the admin or managers can perform this action.'

    def has_permission(self, request, view):
        return is_admin(request.user) or is_manager(request.user)


class IsCustomer(BasePermission):
    """Any authenticated user who is not a manager or delivery crew member."""

    message = 'Only customers can perform this action.'

    def has_permission(self, request, view):
        return is_customer(request.user)
