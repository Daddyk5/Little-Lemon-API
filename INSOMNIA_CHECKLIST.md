# Little Lemon API: Insomnia test checklist

Base URL: `http://127.0.0.1:8000`. Start the server with `python manage.py runserver`.

Header for authenticated requests: `Authorization: Token <token>`.

| User | Token |
|---|---|
| admin (id 1) | `e9c025a2eaec0ee70c583b707d8ccf32e60cd7db` |
| manager1 (id 2) | `86fb8ea7454c5165a2f6520b7d1aa7e68e35ea5d` |
| delivery1 (id 3) | `3c9eebc4890312f300166e189104bd7ad99a6f43` |
| customer1 (id 4) | `2d363bbd033a6fa70b351a66d1e749eb003c1e7d` |
| customer2 (id 5) | `b49e114462c97a8204b11636cc7559ffe774f271` |

Bodies marked *form* use **Form URL Encoded**. Bodies marked *JSON* use **JSON**. Either format works on every endpoint.

**Run order:** steps 8 to 10 need an existing order, so run 18 → 19 → 20 first (customer1 creates order 1), then 8 → 9 → 10.

**Throttling:** menu items and categories allow 10 requests per minute per user. If you get `429`, wait 60 seconds.

---

### 1. Admin assigns a user to the Manager group
- `POST /api/groups/manager/users`
- Header: `Authorization: Token e9c025a2eaec0ee70c583b707d8ccf32e60cd7db` (admin)
- Body (form): `username=customer2`
- Expect **201**: `{"message": "user added to the manager group"}`
- Optional: `DELETE /api/groups/manager/users/5` (admin) returns **200** `{"message": "user removed from the manager group"}`. A user ID that does not exist (`/9999`) returns **404**.

### 2. Access the Manager group with the admin token
- `GET /api/groups/manager/users`
- Header: admin token
- Expect **200**: `[{"id": 2, "username": "manager1", "email": "manager1@littlelemon.com"}, ...]`
- The same request with the manager1 or customer1 token returns **403**. Without a token it returns **401**.

### 3. Admin adds menu items
- `POST /api/menu-items`
- Header: admin token
- Body (JSON): `{"title": "Lemon Tart", "price": "7.50", "category": 2}`
- Expect **201**: `{"id": 7, "title": "Lemon Tart", "price": "7.50", "category": 2, "featured": false}`
- The same request with the customer1 or delivery1 token returns **403**.

### 4. Admin adds categories
- `POST /api/categories`
- Header: admin token
- Body (JSON): `{"slug": "sides", "title": "Sides"}`
- Expect **201**: `{"id": 4, "slug": "sides", "title": "Sides"}`
- The same request with the manager1 token returns **403**.

### 5. Managers log in
- `POST /auth/token/login/`
- No auth header
- Body (form): `username=manager1`, `password=Manager@123`
- Expect **200**: `{"auth_token": "86fb8ea7454c5165a2f6520b7d1aa7e68e35ea5d"}`

### 6. Managers update the item of the day
- `PATCH /api/menu-items/2`
- Header: `Authorization: Token 86fb8ea7454c5165a2f6520b7d1aa7e68e35ea5d` (manager1)
- Body (JSON): `{"featured": true}`
- Expect **200**: `{"id": 2, "title": "Tomato Pasta", "price": "5.00", "category": 1, "featured": true}`
- `GET /api/menu-items?featured=true` now returns only item 2, because the previous item of the day was unset automatically.
- The same PATCH with the customer1 token returns **403**.

### 7. Managers assign users to the delivery crew
- `POST /api/groups/delivery-crew/users`
- Header: manager1 token
- Body (form): `username=customer2`
- Expect **201**: `{"message": "user added to the delivery crew group"}`
- `GET /api/groups/delivery-crew/users` (manager1) lists delivery1 and customer2.
- `DELETE /api/groups/delivery-crew/users/5` returns **200** `{"message": "user removed from the delivery crew group"}`.

### 8. Managers assign orders to the delivery crew
- Requires order 1 from step 20.
- `PATCH /api/orders/1`
- Header: manager1 token
- Body (JSON): `{"delivery_crew": 3}`
- Expect **200**: `{"id": 1, "user": 4, "delivery_crew": 3, "status": false, "total": "...", "date": "...", "order_items": [...]}`
- A user who is not in the Delivery crew group (for example `{"delivery_crew": 4}`) returns **400**.

### 9. Delivery crew accesses assigned orders
- `GET /api/orders`
- Header: `Authorization: Token 3c9eebc4890312f300166e189104bd7ad99a6f43` (delivery1)
- Expect **200**: `{"count": 1, ..., "results": [{"id": 1, "delivery_crew": 3, ...}]}`, showing only orders assigned to delivery1.
- `GET /api/orders/1` (delivery1) returns **200**. An order not assigned to delivery1 returns **403**.

### 10. Delivery crew marks an order as delivered
- `PATCH /api/orders/1`
- Header: delivery1 token
- Body (JSON): `{"status": 1}`
- Expect **200**, with `"status": true` in the response.
- Sending any other field (for example `{"status": 1, "total": "1.00"}`) returns **403**.

### 11. Customers register
- `POST /auth/users/`
- No auth header
- Body (form): `username=customer3`, `email=customer3@test.com`, `password=Lemon@98765`
- Expect **201**: `{"email": "customer3@test.com", "username": "customer3", "id": 6}`

### 12. Customers log in and get tokens
- `POST /auth/token/login/`
- Body (form): `username=customer3`, `password=Lemon@98765`
- Expect **200**: `{"auth_token": "<new token>"}`
- `GET /auth/users/me/` with that token returns **200** `{"email": ..., "id": 6, "username": "customer3"}`.

### 13. Browse all categories
- `GET /api/categories`
- Header: customer1 token
- Expect **200**: `{"count": 3, "next": "...?page=2", "previous": null, "results": [{"id": 1, "slug": "main", "title": "Main"}, ...]}`

### 14. Browse all menu items
- `GET /api/menu-items`
- Header: customer1 token
- Expect **200**:
  ```json
  {"count": 6, "next": "http://127.0.0.1:8000/api/menu-items?page=2", "previous": null,
   "results": [{"id": 1, "title": "Beef Pasta", "price": "12.00", "category": 1, "featured": true},
               {"id": 2, "title": "Tomato Pasta", "price": "5.00", "category": 1, "featured": false}]}
  ```
- Without a token it returns **401**.

### 15. Browse menu items by category
- `GET /api/menu-items?category=2` returns **200**, count 2 (Chocolate Cake, Ice Cream).
- `GET /api/menu-items?category__title=Main` returns **200**, count 3.
- `GET /api/menu-items?search=pasta` returns **200**, count 2.

### 16. Paginate menu items
- `GET /api/menu-items?page=2` returns **200**: results are Grilled Fish and Chocolate Cake, `previous` is `http://127.0.0.1:8000/api/menu-items`, and `next` is `...?page=3`.

### 17. Sort menu items by price
- `GET /api/menu-items?ordering=price` returns **200**, first page Lemonade 3.00 then Ice Cream 4.00.
- `GET /api/menu-items?ordering=-price` returns **200**, first page Grilled Fish 15.00 then Beef Pasta 12.00.

### 18. Add menu items to the cart
- `POST /api/cart/menu-items`
- Header: `Authorization: Token 2d363bbd033a6fa70b351a66d1e749eb003c1e7d` (customer1)
- Body (JSON): `{"menuitem": 1, "quantity": 2}`
- Expect **201**: `{"id": 1, "user": 4, "menuitem": 1, "quantity": 2, "unit_price": "12.00", "price": "24.00"}`
- Add a second item: `{"menuitem": 6, "quantity": 1}` returns **201**.
- The same POST with the manager1 or delivery1 token returns **403**.

### 19. View the cart
- `GET /api/cart/menu-items`
- Header: customer1 token
- Expect **200**: a list containing both cart items.
- `DELETE /api/cart/menu-items` clears the cart and returns **200**. Don't run it before step 20.

### 20. Place an order
- `POST /api/orders`
- Header: customer1 token
- Body: none
- Expect **201**: `{"id": 1, "user": 4, "delivery_crew": null, "status": false, "total": "27.00", "date": "<today>", "order_items": [{"menuitem": 1, "title": "Beef Pasta", "quantity": 2, "unit_price": "12.00", "price": "24.00"}, {"menuitem": 6, "title": "Lemonade", "quantity": 1, ...}]}`
- The cart is now empty. Posting again returns **400** `{"message": "your cart is empty"}`.

### 21. Browse own orders
- `GET /api/orders`
- Header: customer1 token
- Expect **200**: `{"count": 1, ..., "results": [order 1 with its order_items]}`
- `GET /api/orders/1` (customer1) returns **200**. `GET /api/orders/1` with the customer2 token returns **403**.
- For comparison, `GET /api/orders` with the manager1 token returns all orders.
