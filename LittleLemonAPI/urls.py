from django.urls import re_path

from . import views

# Every route works with or without a trailing slash.
urlpatterns = [
    re_path(r'^categories/?$', views.CategoriesView.as_view(), name='categories'),
    re_path(r'^categories/(?P<pk>\d+)/?$', views.SingleCategoryView.as_view(), name='category-detail'),
    re_path(r'^menu-items/?$', views.MenuItemsView.as_view(), name='menu-items'),
    re_path(r'^menu-items/(?P<pk>\d+)/?$', views.SingleMenuItemView.as_view(), name='menu-item-detail'),
    re_path(r'^groups/manager/users/?$', views.ManagerUsersView.as_view(), name='manager-users'),
    re_path(r'^groups/manager/users/(?P<user_id>\d+)/?$', views.ManagerUsersView.as_view(), name='manager-user-detail'),
    re_path(r'^groups/delivery-crew/users/?$', views.DeliveryCrewUsersView.as_view(), name='delivery-crew-users'),
    re_path(r'^groups/delivery-crew/users/(?P<user_id>\d+)/?$', views.DeliveryCrewUsersView.as_view(), name='delivery-crew-user-detail'),
    re_path(r'^cart/menu-items/?$', views.CartView.as_view(), name='cart'),
    re_path(r'^orders/?$', views.OrdersView.as_view(), name='orders'),
    re_path(r'^orders/(?P<pk>\d+)/?$', views.SingleOrderView.as_view(), name='order-detail'),
]
