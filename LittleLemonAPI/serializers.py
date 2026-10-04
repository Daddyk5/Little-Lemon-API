from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Cart, Category, MenuItem, Order, OrderItem
from .permissions import DELIVERY_CREW_GROUP


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'title']


class MenuItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'category', 'featured']
        extra_kwargs = {
            'price': {'min_value': Decimal('0.00')},
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class CartSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    menuitem = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=1000)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'menuitem', 'quantity', 'unit_price', 'price']
        read_only_fields = ['unit_price', 'price']
        # (menuitem, user) uniqueness is handled in the view by merging quantities.
        validators = []


class OrderItemSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='menuitem.title', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'menuitem', 'title', 'quantity', 'unit_price', 'price']


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    delivery_crew = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), allow_null=True, required=False
    )
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'status', 'total', 'date', 'order_items']
        read_only_fields = ['total', 'date']

    def validate_delivery_crew(self, value):
        if value is not None and not value.groups.filter(name=DELIVERY_CREW_GROUP).exists():
            raise serializers.ValidationError('This user is not a member of the delivery crew group.')
        return value


class OrderStatusSerializer(serializers.ModelSerializer):
    """Used by delivery crew: only the status can be changed."""

    class Meta:
        model = Order
        fields = ['status']
        extra_kwargs = {'status': {'required': True}}
