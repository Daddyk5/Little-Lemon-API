from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from .models import Cart, MenuItem, Order

# Sample data and tokens come from migration 0003_sample_data (see notes.txt).
TOKENS = {
    'admin': 'e9c025a2eaec0ee70c583b707d8ccf32e60cd7db',
    'manager1': '86fb8ea7454c5165a2f6520b7d1aa7e68e35ea5d',
    'delivery1': '3c9eebc4890312f300166e189104bd7ad99a6f43',
    'customer1': '2d363bbd033a6fa70b351a66d1e749eb003c1e7d',
    'customer2': 'b49e114462c97a8204b11636cc7559ffe774f271',
}


class LittleLemonAPITests(APITestCase):
    def setUp(self):
        cache.clear()

    def client_for(self, username=None):
        cache.clear()  # keep throttling out of the functional tests
        client = APIClient()
        if username:
            client.credentials(HTTP_AUTHORIZATION='Token ' + TOKENS[username])
        return client

    # 1, 2
    def test_admin_manages_manager_group(self):
        admin = self.client_for('admin')
        r = admin.post('/api/groups/manager/users', {'username': 'customer2'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data, {'message': 'user added to the manager group'})
        r = admin.get('/api/groups/manager/users')
        self.assertEqual(r.status_code, 200)
        self.assertEqual({u['username'] for u in r.data}, {'manager1', 'customer2'})
        user_id = User.objects.get(username='customer2').id
        r = admin.delete(f'/api/groups/manager/users/{user_id}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, {'message': 'user removed from the manager group'})
        self.assertEqual(admin.delete('/api/groups/manager/users/9999').status_code, 404)
        self.assertEqual(self.client_for('manager1').get('/api/groups/manager/users').status_code, 403)
        self.assertEqual(self.client_for().get('/api/groups/manager/users').status_code, 401)

    # 3, 4
    def test_admin_adds_categories_and_menu_items(self):
        admin = self.client_for('admin')
        r = admin.post('/api/categories', {'slug': 'sides', 'title': 'Sides'})
        self.assertEqual(r.status_code, 201)
        r = admin.post('/api/menu-items', {'title': 'Fries', 'price': '2.50', 'category': r.data['id']})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(list(r.data.keys()), ['id', 'title', 'price', 'category', 'featured'])
        self.assertEqual(r.data['price'], '2.50')
        self.assertEqual(self.client_for('manager1').post('/api/categories', {'slug': 'x', 'title': 'X'}).status_code, 403)
        self.assertEqual(self.client_for('customer1').post('/api/menu-items', {'title': 'X', 'price': '1', 'category': 1}).status_code, 403)
        self.assertEqual(self.client_for('delivery1').post('/api/menu-items', {'title': 'X', 'price': '1', 'category': 1}).status_code, 403)

    # 5, 12
    def test_login_returns_token(self):
        r = self.client_for().post('/auth/token/login/', {'username': 'manager1', 'password': 'Manager@123'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('auth_token', r.data)
        r = self.client_for().post('/auth/token/login/', {'username': 'customer1', 'password': 'Customer@123'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['auth_token'], TOKENS['customer1'])

    # 6
    def test_manager_sets_item_of_the_day(self):
        manager = self.client_for('manager1')
        r = manager.patch('/api/menu-items/3', {'featured': True}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['featured'])
        self.assertEqual(list(MenuItem.objects.filter(featured=True).values_list('id', flat=True)), [3])
        self.assertEqual(self.client_for('customer1').patch('/api/menu-items/3', {'featured': True}, format='json').status_code, 403)

    # 7, 8, 9, 10, 20, 21
    def test_order_flow(self):
        customer = self.client_for('customer1')
        self.assertEqual(customer.post('/api/orders').status_code, 400)  # empty cart

        # 18, 19
        r = customer.post('/api/cart/menu-items', {'menuitem': 1, 'quantity': 2})
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['unit_price'], r.data['price']), ('12.00', '24.00'))
        customer.post('/api/cart/menu-items', {'menuitem': 6, 'quantity': 1})
        r = self.client_for('customer1').get('/api/cart/menu-items')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 2)

        r = self.client_for('customer1').post('/api/orders')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['total'], '27.00')
        self.assertEqual(len(r.data['order_items']), 2)
        self.assertFalse(Cart.objects.filter(user__username='customer1').exists())
        order_id = r.data['id']

        r = self.client_for('customer1').get('/api/orders')
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(self.client_for('customer2').get('/api/orders').data['count'], 0)
        self.assertEqual(self.client_for('customer2').get(f'/api/orders/{order_id}').status_code, 403)
        self.assertEqual(self.client_for('customer1').get(f'/api/orders/{order_id}').status_code, 200)

        # 7: manager assigns customer2 to delivery crew
        r = self.client_for('manager1').post('/api/groups/delivery-crew/users', {'username': 'customer2'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data, {'message': 'user added to the delivery crew group'})

        delivery1_id = User.objects.get(username='delivery1').id
        self.assertEqual(self.client_for('delivery1').get(f'/api/orders/{order_id}').status_code, 403)
        # 8
        r = self.client_for('manager1').patch(f'/api/orders/{order_id}', {'delivery_crew': delivery1_id}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['delivery_crew'], delivery1_id)
        r = self.client_for('manager1').patch(f'/api/orders/{order_id}', {'delivery_crew': User.objects.get(username='customer1').id}, format='json')
        self.assertEqual(r.status_code, 400)
        # 9
        r = self.client_for('delivery1').get('/api/orders')
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(self.client_for('customer2').get('/api/orders').data['count'], 0)
        # 10
        r = self.client_for('delivery1').patch(f'/api/orders/{order_id}', {'status': 1}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['status'])
        r = self.client_for('delivery1').patch(f'/api/orders/{order_id}', {'status': 0, 'total': '1.00'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client_for('customer1').patch(f'/api/orders/{order_id}', {'status': 1}, format='json').status_code, 403)
        self.assertEqual(self.client_for('delivery1').delete(f'/api/orders/{order_id}').status_code, 403)
        self.assertEqual(self.client_for('manager1').get('/api/orders').data['count'], 1)
        self.assertEqual(self.client_for('manager1').delete(f'/api/orders/{order_id}').status_code, 200)
        self.assertFalse(Order.objects.exists())

        # clear cart
        customer = self.client_for('customer1')
        customer.post('/api/cart/menu-items', {'menuitem': 2, 'quantity': 1})
        self.assertEqual(self.client_for('customer1').delete('/api/cart/menu-items').status_code, 200)
        self.assertEqual(self.client_for('customer1').get('/api/cart/menu-items').data, [])

    # 11
    def test_customer_registers(self):
        r = self.client_for().post('/auth/users/', {'username': 'newbie', 'email': 'n@x.com', 'password': 'Lemon@98765'})
        self.assertEqual(r.status_code, 201)
        r = self.client_for().post('/auth/token/login/', {'username': 'newbie', 'password': 'Lemon@98765'})
        token = r.data['auth_token']
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        self.assertEqual(client.get('/auth/users/me/').data['username'], 'newbie')

    # 13 - 17
    def test_browse_filter_sort_paginate(self):
        r = self.client_for('customer1').get('/api/categories')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        r = self.client_for('customer1').get('/api/menu-items')
        self.assertEqual(r.data['count'], 6)
        self.assertEqual(r.data['next'], 'http://testserver/api/menu-items?page=2')
        self.assertIsNone(r.data['previous'])
        self.assertEqual(r.data['results'][0], {'id': 1, 'title': 'Beef Pasta', 'price': '12.00', 'category': 1, 'featured': True})
        self.assertEqual(self.client_for('customer1').get('/api/menu-items?category=2').data['count'], 2)
        self.assertEqual(self.client_for('customer1').get('/api/menu-items?category__title=Main').data['count'], 3)
        r = self.client_for('customer1').get('/api/menu-items?ordering=price')
        self.assertEqual([i['title'] for i in r.data['results']], ['Lemonade', 'Ice Cream'])
        r = self.client_for('customer1').get('/api/menu-items?ordering=-price')
        self.assertEqual([i['title'] for i in r.data['results']], ['Grilled Fish', 'Beef Pasta'])
        self.assertEqual(self.client_for('customer1').get('/api/menu-items?search=pasta').data['count'], 2)
        r = self.client_for('customer1').get('/api/menu-items?page=3')
        self.assertEqual([i['id'] for i in r.data['results']], [5, 6])
        self.assertEqual(self.client_for().get('/api/menu-items').status_code, 401)

    def test_user_throttle(self):
        client = self.client_for('customer1')
        codes = [client.get('/api/menu-items').status_code for _ in range(11)]
        self.assertEqual(codes[:10], [200] * 10)
        self.assertEqual(codes[10], 429)
