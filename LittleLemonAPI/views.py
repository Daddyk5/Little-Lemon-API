from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from .models import Cart, Category, MenuItem, Order, OrderItem
from .permissions import (
    DELIVERY_CREW_GROUP,
    MANAGER_GROUP,
    IsAdminOrManager,
    IsCustomer,
    is_admin,
    is_delivery_crew,
    is_manager,
)
from .serializers import (
    CartSerializer,
    CategorySerializer,
    MenuItemSerializer,
    OrderSerializer,
    OrderStatusSerializer,
    UserSerializer,
)


# ---------------------------------------------------------------- Categories

class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by('id')
    serializer_class = CategorySerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    search_fields = ['title', 'slug']
    ordering_fields = ['id', 'title']

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminUser()]


class SingleCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.menuitem_set.exists():
            return Response(
                {'message': 'This category still has menu items and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


# ---------------------------------------------------------------- Menu items

class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.select_related('category').all().order_by('id')
    serializer_class = MenuItemSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    filterset_fields = {
        'category': ['exact'],
        'category__title': ['exact', 'iexact'],
        'featured': ['exact'],
        'price': ['exact', 'lte', 'gte'],
    }
    ordering_fields = ['id', 'price', 'title', 'category']
    search_fields = ['title', 'category__title']

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminOrManager()]


class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminOrManager()]


# ---------------------------------------------------------- Group management

class GroupUsersView(APIView):
    """List users in a group, add a user by username, remove a user by id."""

    group_name = None
    label = None

    def get_group(self):
        group, _ = Group.objects.get_or_create(name=self.group_name)
        return group

    def get(self, request, user_id=None):
        group = self.get_group()
        if user_id is not None:
            user = get_object_or_404(group.user_set, pk=user_id)
            return Response(UserSerializer(user).data)
        users = group.user_set.all().order_by('id')
        return Response(UserSerializer(users, many=True).data)

    def post(self, request, user_id=None):
        username = request.data.get('username')
        if not username:
            return Response({'message': 'username is required'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, username=username)
        self.get_group().user_set.add(user)
        return Response(
            {'message': f'user added to the {self.label} group'},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, user_id=None):
        if user_id is None:
            return Response(
                {'message': 'user id is required in the URL'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        group = self.get_group()
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return Response({'message': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
        if not group.user_set.filter(pk=user.pk).exists():
            return Response(
                {'message': f'user is not in the {self.label} group'},
                status=status.HTTP_404_NOT_FOUND,
            )
        group.user_set.remove(user)
        return Response(
            {'message': f'user removed from the {self.label} group'},
            status=status.HTTP_200_OK,
        )


class ManagerUsersView(GroupUsersView):
    group_name = MANAGER_GROUP
    label = 'manager'
    permission_classes = [IsAdminUser]


class DeliveryCrewUsersView(GroupUsersView):
    group_name = DELIVERY_CREW_GROUP
    label = 'delivery crew'
    permission_classes = [IsAdminOrManager]


# ---------------------------------------------------------------------- Cart

class CartView(generics.ListCreateAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsCustomer]
    pagination_class = None

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related('menuitem').order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        menuitem = serializer.validated_data['menuitem']
        quantity = serializer.validated_data['quantity']

        cart_item = Cart.objects.filter(user=request.user, menuitem=menuitem).first()
        if cart_item:
            # Same item added again: increase the quantity.
            cart_item.quantity += quantity
            cart_item.unit_price = menuitem.price
            cart_item.price = menuitem.price * cart_item.quantity
            cart_item.save()
        else:
            cart_item = Cart.objects.create(
                user=request.user,
                menuitem=menuitem,
                quantity=quantity,
                unit_price=menuitem.price,
                price=menuitem.price * quantity,
            )
        return Response(CartSerializer(cart_item).data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        deleted, _ = Cart.objects.filter(user=request.user).delete()
        return Response(
            {'message': f'cart cleared ({deleted} item(s) removed)'},
            status=status.HTTP_200_OK,
        )


# -------------------------------------------------------------------- Orders

class OrdersView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    filterset_fields = ['status', 'delivery_crew', 'date']
    ordering_fields = ['id', 'date', 'total', 'status']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsCustomer()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.prefetch_related('order_items__menuitem').order_by('id')
        if is_admin(user) or is_manager(user):
            return queryset
        if is_delivery_crew(user):
            return queryset.filter(delivery_crew=user)
        return queryset.filter(user=user)

    def create(self, request, *args, **kwargs):
        cart_items = list(Cart.objects.filter(user=request.user).select_related('menuitem'))
        if not cart_items:
            return Response({'message': 'your cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            total = sum((item.price for item in cart_items), Decimal('0.00'))
            order = Order.objects.create(
                user=request.user, total=total, date=date.today(), status=False
            )
            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    menuitem=item.menuitem,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    price=item.price,
                )
                for item in cart_items
            ])
            Cart.objects.filter(user=request.user).delete()

        order = Order.objects.prefetch_related('order_items__menuitem').get(pk=order.pk)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class SingleOrderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.prefetch_related('order_items__menuitem')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        order = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        user = self.request.user
        if is_admin(user) or is_manager(user):
            return order
        if is_delivery_crew(user):
            if order.delivery_crew_id != user.id:
                raise PermissionDenied('This order is not assigned to you.')
            return order
        if order.user_id != user.id:
            raise PermissionDenied('You can only view your own orders.')
        return order

    def update(self, request, *args, **kwargs):
        user = request.user
        if is_admin(user) or is_manager(user):
            # Managers can assign delivery crew and set status (PUT behaves like PATCH).
            order = self.get_object()
            serializer = OrderSerializer(order, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        if is_delivery_crew(user):
            sent_fields = {key for key in request.data.keys() if key != 'csrfmiddlewaretoken'}
            if sent_fields != {'status'}:
                raise PermissionDenied('Delivery crew can only update the order status.')
            order = self.get_object()
            serializer = OrderStatusSerializer(order, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(OrderSerializer(order).data)

        raise PermissionDenied('Only managers and delivery crew can update orders.')

    def destroy(self, request, *args, **kwargs):
        if not (is_admin(request.user) or is_manager(request.user)):
            raise PermissionDenied('Only managers can delete orders.')
        order = self.get_object()
        order_id = order.pk
        order.delete()
        return Response({'message': f'order {order_id} deleted'}, status=status.HTTP_200_OK)
