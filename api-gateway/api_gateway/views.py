import requests
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.http import JsonResponse
from django.shortcuts import redirect, render


BOOK_SERVICE_URL = "http://book-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
CART_SERVICE_URL = "http://cart-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8000"
RECOMMENDER_AI_SERVICE_URL = "http://recommender-ai-service:8000"
AUTH_SERVICE_URL = "http://auth-service:8000"


def _safe_get_json(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json(), None
        return [], f"GET {url} failed with status {response.status_code}"
    except requests.RequestException as exc:
        return [], str(exc)


def _to_int(value, default=0):
    return int(value or default)


def _post_json_with_error(url, payload, error_prefix):
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code in [200, 201, 202]:
            return None
        return f"{error_prefix}: {response.text}"
    except requests.RequestException as exc:
        return str(exc)


def _set_book_stock(book_id, stock_value):
    try:
        response = requests.put(
            f"{BOOK_SERVICE_URL}/books/{book_id}/",
            json={"stock": stock_value},
            timeout=5,
        )
        if response.status_code not in [200, 201]:
            return f"Update stock failed for book #{book_id}: {response.text}"
        return None
    except requests.RequestException as exc:
        return str(exc)


def _reserve_stock_for_items(items, book_map):
    original_stocks = {}

    for item in items:
        book_id = item.get("book_id")
        book = book_map.get(book_id)
        quantity = int(item.get("quantity", 0) or 0)

        if not book:
            return None, f"Book #{book_id} no longer exists."

        current_stock = int(book.get("stock", 0) or 0)
        if quantity <= 0:
            return None, f"Invalid quantity for {book.get('title', f'Book #{book_id}')}."
        if current_stock < quantity:
            return None, f"Not enough stock for {book.get('title', f'Book #{book_id}')}. Remaining: {current_stock}."

        original_stocks[book_id] = current_stock

    for item in items:
        book_id = item.get("book_id")
        quantity = int(item.get("quantity", 0) or 0)
        update_error = _set_book_stock(book_id, original_stocks[book_id] - quantity)
        if update_error:
            _restore_stock(original_stocks)
            return None, update_error

    return original_stocks, None


def _restore_stock(original_stocks):
    for book_id, stock_value in original_stocks.items():
        _set_book_stock(book_id, stock_value)


def _get_user_role(user):
    if user.groups.filter(name="staff").exists() or user.is_staff:
        return "staff"
    if user.groups.filter(name="customer").exists():
        return "customer"
    return None


def _ensure_customer_for_user(user):
    customer_email = f"{user.username}@customer.local"
    try:
        list_resp = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=5)
        if list_resp.status_code != 200:
            return None, "Cannot fetch customer list"

        customers = list_resp.json()
        existing = next((c for c in customers if c.get("email") == customer_email), None)
        if existing:
            return existing.get("id"), None

        create_resp = requests.post(
            f"{CUSTOMER_SERVICE_URL}/customers/",
            json={"name": user.username, "email": customer_email},
            timeout=5,
        )
        if create_resp.status_code not in [200, 201]:
            return None, f"Create customer failed: {create_resp.text}"

        return create_resp.json().get("id"), None
    except requests.RequestException as exc:
        return None, str(exc)


def _get_customer_for_user(user):
    lookup_emails = []
    if user.email:
        lookup_emails.append(user.email)
    legacy_email = f"{user.username}@customer.local"
    if legacy_email not in lookup_emails:
        lookup_emails.append(legacy_email)

    try:
        list_resp = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=5)
        if list_resp.status_code != 200:
            return None, "Cannot fetch customer list"

        customers = list_resp.json()
        existing = next((c for c in customers if c.get("email") in lookup_emails), None)
        return existing, None
    except requests.RequestException as exc:
        return None, str(exc)


def _refresh_session_jwt(request, username, role):
    try:
        auth_resp = requests.post(
            f"{AUTH_SERVICE_URL}/auth/login/",
            json={"username": username, "role": role},
            timeout=5,
        )
        if auth_resp.status_code != 200:
            return f"Auth service login failed: {auth_resp.text}"

        token = auth_resp.json().get("access_token")
        if not token:
            return "Auth service did not return token."

        request.session["jwt_token"] = token
        return None
    except requests.RequestException as exc:
        return str(exc)


def _ensure_cart_for_customer(customer_id):
    try:
        resp = requests.post(f"{CART_SERVICE_URL}/carts/by-customer/{customer_id}/", timeout=5)
        if resp.status_code not in [200, 201]:
            return None, f"Ensure cart failed: {resp.text}"
        return resp.json(), None
    except requests.RequestException as exc:
        return None, str(exc)


def home(request):
    if not request.user.is_authenticated:
        return redirect("login")

    role = _get_user_role(request.user) or "customer"
    template_name = "staff_home.html" if role == "staff" else "customer_home.html"
    return render(request, template_name, {"role": role})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    error = None
    if request.method == "POST" and not error:
        username = request.POST.get("username", "").strip()
        role = request.POST.get("role", "customer").strip().lower()

        if not username:
            error = "Username is required."
        elif role not in {"customer", "staff"}:
            error = "Invalid role selected."
        else:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": role == "staff"},
            )

            if created:
                # Demo flow: user is auto-created at first login.
                user.set_unusable_password()
                user.save(update_fields=["password"])

            existing_role = _get_user_role(user)
            if existing_role and existing_role != role:
                error = f"User '{username}' already exists with role '{existing_role}'."
            else:
                role_group, _ = Group.objects.get_or_create(name=role)
                if not user.groups.filter(name=role).exists():
                    user.groups.add(role_group)

                if role == "staff" and not user.is_staff:
                    user.is_staff = True
                    user.save(update_fields=["is_staff"])

                if role == "customer":
                    customer_id, customer_err = _ensure_customer_for_user(user)
                    if customer_err:
                        error = customer_err
                    else:
                        _, cart_err = _ensure_cart_for_customer(customer_id)
                        if cart_err:
                            error = cart_err

                if not error:
                    # ADDED-ASSIGNMENT06: request JWT from auth-service then store in session.
                    try:
                        auth_resp = requests.post(
                            f"{AUTH_SERVICE_URL}/auth/login/",
                            json={"username": username, "role": role},
                            timeout=5,
                        )
                        if auth_resp.status_code != 200:
                            error = f"Auth service login failed: {auth_resp.text}"
                        else:
                            token = auth_resp.json().get("access_token")
                            if not token:
                                error = "Auth service did not return token."
                            else:
                                request.session["jwt_token"] = token
                    except requests.RequestException as exc:
                        error = str(exc)

                if not error:
                    login(request, user)
                    return redirect("home")

    return render(request, "login.html", {"error": error})


def logout_view(request):
    # ADDED-ASSIGNMENT06: remove JWT on logout.
    request.session.pop("jwt_token", None)
    logout(request)
    return redirect("login")


def health(request):
    # ADDED-ASSIGNMENT06: basic observability endpoint for gateway.
    return JsonResponse({"status": "ok", "service": "api-gateway"})


@login_required
def account_detail(request):
    role = _get_user_role(request.user) or "customer"
    group_names = list(request.user.groups.values_list("name", flat=True))
    jwt_payload = getattr(request, "jwt_payload", {}) or {}
    customer = None
    cart = None
    error = None
    success = None

    if request.method == "POST":
        new_username = request.POST.get("username", "").strip()
        new_name = request.POST.get("name", "").strip()
        new_email = request.POST.get("email", "").strip()

        if not new_username:
            error = "Username is required."
        elif role == "customer" and (not new_name or not new_email):
            error = "Name and email are required for customer accounts."
        elif new_username != request.user.username and User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
            error = f"Username '{new_username}' is already in use."
        else:
            existing_customer = None
            if role == "customer":
                existing_customer, customer_error = _get_customer_for_user(request.user)
                if customer_error:
                    error = customer_error
                elif not existing_customer:
                    error = "Customer profile not found."

            if not error:
                old_username = request.user.username
                old_first_name = request.user.first_name
                old_email = request.user.email
                request.user.username = new_username
                request.user.first_name = new_name
                request.user.email = new_email
                try:
                    request.user.save(update_fields=["username", "first_name", "email"])
                except Exception as exc:
                    error = str(exc)

                if not error and role == "customer":
                    customer_resp = requests.put(
                        f"{CUSTOMER_SERVICE_URL}/customers/{existing_customer.get('id')}/",
                        json={"name": new_name, "email": new_email},
                        timeout=5,
                    )
                    if customer_resp.status_code not in [200, 201]:
                        request.user.username = old_username
                        request.user.first_name = old_first_name
                        request.user.email = old_email
                        request.user.save(update_fields=["username", "first_name", "email"])
                        error = f"Update customer profile failed: {customer_resp.text}"

                if not error:
                    jwt_error = _refresh_session_jwt(request, request.user.username, role)
                    if jwt_error:
                        error = f"Account updated, but session refresh failed: {jwt_error}"
                    else:
                        success = "Account updated successfully."

    if role == "customer":
        customer, error = _get_customer_for_user(request.user)
        if customer and not error:
            cart, cart_error = _ensure_cart_for_customer(customer.get("id"))
            if cart_error:
                error = cart_error

    form_name = customer.get("name") if customer else request.user.first_name
    form_email = customer.get("email") if customer else request.user.email

    return render(
        request,
        "account_detail.html",
        {
            "role": role,
            "group_names": group_names,
            "jwt_payload": jwt_payload,
            "customer": customer,
            "cart": cart,
            "error": error,
            "success": success,
            "form_username": request.user.username,
            "form_name": form_name,
            "form_email": form_email,
        },
    )


@login_required
def book_list(request):
    error = None
    role = _get_user_role(request.user) or "customer"
    is_customer = role == "customer"
    search_query = request.GET.get("q", "").strip()

    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            if is_customer and action == "add_to_cart":
                customer_id, customer_err = _ensure_customer_for_user(request.user)
                if customer_err:
                    error = customer_err
                else:
                    cart, cart_err = _ensure_cart_for_customer(customer_id)
                    if cart_err:
                        error = cart_err
                    else:
                        payload = {
                            "cart": cart.get("id"),
                            "book_id": _to_int(request.POST.get("book_id", "0"), 0),
                            "quantity": _to_int(request.POST.get("quantity", "1"), 1),
                        }
                        error = _post_json_with_error(f"{CART_SERVICE_URL}/cart-items/", payload, "Add to cart failed")
                        if not error:
                            return redirect("books")
            elif not is_customer:
                if action == "update_book":
                    book_id = int(request.POST.get("book_id", "0") or 0)
                    payload = {
                        "title": request.POST.get("title", ""),
                        "author": request.POST.get("author", ""),
                        "price": request.POST.get("price", "0"),
                        "stock": int(request.POST.get("stock", "0") or 0),
                    }
                    update_resp = requests.put(f"{BOOK_SERVICE_URL}/books/{book_id}/", json=payload, timeout=5)
                    if update_resp.status_code not in [200, 201]:
                        error = f"Update book failed: {update_resp.text}"
                    else:
                        return redirect("books")
                elif action == "delete_book":
                    book_id = int(request.POST.get("book_id", "0") or 0)
                    delete_resp = requests.delete(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=5)
                    if delete_resp.status_code not in [200, 204]:
                        error = f"Delete book failed: {delete_resp.text}"
                    else:
                        return redirect("books")
                else:
                    payload = {
                        "title": request.POST.get("title", ""),
                        "author": request.POST.get("author", ""),
                        "price": request.POST.get("price", "0"),
                        "stock": int(request.POST.get("stock", "0") or 0),
                    }
                    create_resp = requests.post(f"{BOOK_SERVICE_URL}/books/", json=payload, timeout=5)
                    if create_resp.status_code not in [200, 201]:
                        error = f"Create book failed: {create_resp.text}"
                    else:
                        return redirect("books")
            else:
                error = "Unsupported action for customer."
        except (TypeError, ValueError):
            error = "Invalid numeric input."
        except requests.RequestException as exc:
            error = str(exc)

    books, fetch_error = _safe_get_json(f"{BOOK_SERVICE_URL}/books/")
    if isinstance(books, list) and search_query:
        needle = search_query.lower()
        books = [
            book
            for book in books
            if needle in str(book.get("title", "")).lower() or needle in str(book.get("author", "")).lower()
        ]

    return render(
        request,
        "books.html",
        {
            "books": books,
            "error": error or fetch_error,
            "is_customer": is_customer,
            "search_query": search_query,
        },
    )


@login_required
def book_detail(request, book_id):
    error = None
    role = _get_user_role(request.user) or "customer"
    is_customer = role == "customer"
    current_customer_id = None

    if is_customer:
        current_customer_id, customer_err = _ensure_customer_for_user(request.user)
        if customer_err:
            error = customer_err

    if request.method == "POST" and is_customer and not error:
        try:
            rating_value = _to_int(request.POST.get("rating", "0"), 0)
            comment_value = request.POST.get("comment", "").strip()

            if rating_value < 1 or rating_value > 5:
                error = "Rating must be between 1 and 5."
            elif not comment_value:
                error = "Comment is required."
            else:
                payload = {
                    "customer_id": current_customer_id,
                    "book_id": book_id,
                    "rating": rating_value,
                    "comment": comment_value,
                }
                create_resp = requests.post(f"{COMMENT_RATE_SERVICE_URL}/ratings/", json=payload, timeout=5)
                if create_resp.status_code not in [200, 201]:
                    error = f"Create rating failed: {create_resp.text}"
                else:
                    return redirect("book_detail", book_id=book_id)
        except (TypeError, ValueError):
            error = "Invalid rating value."
        except requests.RequestException as exc:
            error = str(exc)

    try:
        response = requests.get(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=5)
        if response.status_code == 200:
            book = response.json()
        else:
            book = None
            error = f"Book not found (status {response.status_code})"
    except requests.RequestException as exc:
        book = None
        error = str(exc)

    reviews = []
    average_rating = 0
    average_stars = "-----"
    rating_count = 0

    ratings, ratings_error = _safe_get_json(f"{COMMENT_RATE_SERVICE_URL}/ratings/")
    if not error and ratings_error:
        error = ratings_error

    customers, customers_error = _safe_get_json(f"{CUSTOMER_SERVICE_URL}/customers/")
    if not error and customers_error:
        error = customers_error

    if isinstance(ratings, list):
        review_rows = [rating for rating in ratings if rating.get("book_id") == book_id]
        review_rows.sort(key=lambda r: r.get("id", 0), reverse=True)
        rating_count = len(review_rows)

        customer_map = {}
        if isinstance(customers, list):
            customer_map = {customer.get("id"): customer for customer in customers}

        total_rating = 0
        for row in review_rows:
            value = int(row.get("rating", 0) or 0)
            total_rating += value
            stars = "*" * value + "-" * (5 - value)

            customer = customer_map.get(row.get("customer_id"), {})
            customer_name = customer.get("name") or f"Customer #{row.get('customer_id')}"

            reviews.append(
                {
                    "id": row.get("id"),
                    "customer_name": customer_name,
                    "rating": value,
                    "stars": stars,
                    "comment": row.get("comment", ""),
                }
            )

        if rating_count > 0:
            average_rating = round(total_rating / rating_count, 2)
            rounded = int(round(average_rating))
            average_stars = "*" * rounded + "-" * (5 - rounded)

    return render(
        request,
        "book_detail.html",
        {
            "book": book,
            "book_id": book_id,
            "error": error,
            "is_customer": is_customer,
            "reviews": reviews,
            "average_rating": average_rating,
            "average_stars": average_stars,
            "rating_count": rating_count,
        },
    )


@login_required
def customer_list(request):
    error = None
    if request.method == "POST":
        payload = {
            "name": request.POST.get("name", ""),
            "email": request.POST.get("email", ""),
        }
        error = _post_json_with_error(f"{CUSTOMER_SERVICE_URL}/customers/", payload, "Create customer failed")
        if not error:
            return redirect("customers")

    customers, fetch_error = _safe_get_json(f"{CUSTOMER_SERVICE_URL}/customers/")
    return render(request, "customers.html", {"customers": customers, "error": error or fetch_error})


@login_required
def cart_list(request):
    error = None
    role = _get_user_role(request.user) or "customer"
    is_customer = role == "customer"

    current_customer_id = None
    current_cart = None
    current_items = []
    cart_total = 0
    if is_customer:
        current_customer_id, customer_err = _ensure_customer_for_user(request.user)
        if customer_err:
            error = customer_err
        else:
            current_cart, cart_err = _ensure_cart_for_customer(current_customer_id)
            if cart_err:
                error = cart_err

    if request.method == "POST" and not error:
        action = request.POST.get("action", "")
        try:
            if is_customer:
                cart_id = current_cart.get("id") if current_cart else None
                if not cart_id:
                    error = "Customer cart is not available."
                elif action == "add_item":
                    payload = {
                        "cart": cart_id,
                        "book_id": _to_int(request.POST.get("book_id", "0"), 0),
                        "quantity": _to_int(request.POST.get("quantity", "1"), 1),
                    }
                    error = _post_json_with_error(f"{CART_SERVICE_URL}/cart-items/", payload, "Add item failed")
                    if not error:
                        return redirect("carts")
                elif action == "update_item":
                    item_id = _to_int(request.POST.get("item_id", "0"), 0)
                    payload = {"quantity": _to_int(request.POST.get("quantity", "1"), 1)}
                    resp = requests.put(f"{CART_SERVICE_URL}/cart-items/{item_id}/", json=payload, timeout=5)
                    if resp.status_code not in [200, 201]:
                        error = f"Update item failed: {resp.text}"
                    else:
                        return redirect("carts")
                elif action == "delete_item":
                    item_id = _to_int(request.POST.get("item_id", "0"), 0)
                    resp = requests.delete(f"{CART_SERVICE_URL}/cart-items/{item_id}/", timeout=5)
                    if resp.status_code not in [200, 204]:
                        error = f"Delete item failed: {resp.text}"
                    else:
                        return redirect("carts")
                else:
                    error = "Unsupported cart action."
            else:
                payload = {"customer_id": _to_int(request.POST.get("customer_id", "0"), 0)}
                error = _post_json_with_error(f"{CART_SERVICE_URL}/carts/", payload, "Create cart failed")
                if not error:
                    return redirect("carts")
        except (TypeError, ValueError):
            error = "Invalid numeric input."
        except requests.RequestException as exc:
            error = str(exc)

    if is_customer and current_cart and not error:
        items_url = f"{CART_SERVICE_URL}/carts/{current_cart.get('id')}/items/"
        current_items, item_err = _safe_get_json(items_url)
        if item_err:
            error = item_err

    if is_customer and current_items and not error:
        books, books_err = _safe_get_json(f"{BOOK_SERVICE_URL}/books/")
        if books_err:
            error = books_err
        else:
            book_map = {book.get("id"): book for book in books}
            for item in current_items:
                book = book_map.get(item.get("book_id"))
                unit_price = float(book.get("price", 0)) if book else 0
                quantity = int(item.get("quantity", 0) or 0)
                item["book_title"] = book.get("title") if book else f"Book #{item.get('book_id')}"
                item["unit_price"] = unit_price
                item["item_total"] = round(unit_price * quantity, 2)

            cart_total = round(sum(float(item.get("item_total", 0) or 0) for item in current_items), 2)

    return render(
        request,
        "carts.html",
        {
            "error": error,
            "is_customer": is_customer,
            "current_customer_id": current_customer_id,
            "current_cart": current_cart,
            "current_items": current_items,
            "cart_total": cart_total,
        },
    )


@login_required
def cart_item_detail(request, item_id):
    error = None
    item = None
    book = None
    unit_price = 0
    item_total = 0

    try:
        item_resp = requests.get(f"{CART_SERVICE_URL}/cart-items/{item_id}/", timeout=5)
        if item_resp.status_code != 200:
            error = f"Cart item not found (status {item_resp.status_code})"
        else:
            item = item_resp.json()
    except requests.RequestException as exc:
        error = str(exc)

    if item and not error:
        try:
            book_resp = requests.get(f"{BOOK_SERVICE_URL}/books/{item.get('book_id')}/", timeout=5)
            if book_resp.status_code == 200:
                book = book_resp.json()
                unit_price = float(book.get("price", 0))
            else:
                error = f"Book not found (status {book_resp.status_code})"
        except requests.RequestException as exc:
            error = str(exc)

    if item and not error:
        item_total = round(unit_price * int(item.get("quantity", 0) or 0), 2)

    return render(
        request,
        "cart_item_detail.html",
        {
            "error": error,
            "item": item,
            "book": book,
            "unit_price": unit_price,
            "item_total": item_total,
        },
    )


@login_required
def checkout(request):
    error = None
    role = _get_user_role(request.user) or "customer"
    is_customer = role == "customer"

    if not is_customer:
        return render(request, "checkout.html", {"error": "Only customer can checkout.", "current_items": [], "cart_total": 0})

    current_customer_id, customer_err = _ensure_customer_for_user(request.user)
    if customer_err:
        return render(request, "checkout.html", {"error": customer_err, "current_items": [], "cart_total": 0})

    current_cart, cart_err = _ensure_cart_for_customer(current_customer_id)
    if cart_err:
        return render(request, "checkout.html", {"error": cart_err, "current_items": [], "cart_total": 0})

    items_url = f"{CART_SERVICE_URL}/carts/{current_cart.get('id')}/items/"
    current_items, item_err = _safe_get_json(items_url)
    if item_err:
        return render(request, "checkout.html", {"error": item_err, "current_items": [], "cart_total": 0})

    if not current_items:
        return render(
            request,
            "checkout.html",
            {
                "error": "Your cart is empty.",
                "current_items": [],
                "cart_total": 0,
                "current_customer_id": current_customer_id,
            },
        )

    books, books_err = _safe_get_json(f"{BOOK_SERVICE_URL}/books/")
    if books_err:
        error = books_err
        books = []

    book_map = {book.get("id"): book for book in books}
    for item in current_items:
        book = book_map.get(item.get("book_id"))
        unit_price = float(book.get("price", 0)) if book else 0
        quantity = int(item.get("quantity", 0) or 0)
        item["book_title"] = book.get("title") if book else f"Book #{item.get('book_id')}"
        item["unit_price"] = unit_price
        item["item_total"] = round(unit_price * quantity, 2)

    cart_total = round(sum(float(item.get("item_total", 0) or 0) for item in current_items), 2)

    if request.method == "POST" and not error:
        original_stocks, stock_error = _reserve_stock_for_items(current_items, book_map)
        if stock_error:
            error = stock_error

        payload = {
            "customer_id": current_customer_id,
            # ADDED-ASSIGNMENT06: force normal saga path from gateway UI (fault simulation disabled).
            "simulate_payment_fail": False,
            "simulate_shipping_fail": False,
        }
        if not error:
            error = _post_json_with_error(f"{ORDER_SERVICE_URL}/orders/", payload, "Checkout failed")

        if error and original_stocks:
            _restore_stock(original_stocks)

        if not error:
            for item in current_items:
                item_id = item.get("id")
                try:
                    requests.delete(f"{CART_SERVICE_URL}/cart-items/{item_id}/", timeout=5)
                except requests.RequestException:
                    # Best effort cleanup; order is already created.
                    pass
            return redirect("orders")

    return render(
        request,
        "checkout.html",
        {
            "error": error,
            "current_items": current_items,
            "cart_total": cart_total,
            "current_customer_id": current_customer_id,
        },
    )


@login_required
def order_list(request):
    error = None
    role = _get_user_role(request.user) or "customer"
    is_customer = role == "customer"
    current_customer_id = None

    if is_customer:
        current_customer_id, customer_err = _ensure_customer_for_user(request.user)
        if customer_err:
            error = customer_err

    if request.method == "POST" and not is_customer:
        try:
            customer_id_value = current_customer_id if is_customer else _to_int(request.POST.get("customer_id", "0"), 0)
            payload = {
                "customer_id": customer_id_value,
                # ADDED-ASSIGNMENT06: force normal saga path from gateway UI (fault simulation disabled).
                "simulate_payment_fail": False,
                "simulate_shipping_fail": False,
            }
            error = _post_json_with_error(f"{ORDER_SERVICE_URL}/orders/", payload, "Create order failed")
            if not error:
                return redirect("orders")
        except (TypeError, ValueError):
            error = "Invalid customer_id input."

    orders, fetch_error = _safe_get_json(f"{ORDER_SERVICE_URL}/orders/")

    if is_customer and isinstance(orders, list):
        orders = [order for order in orders if order.get("customer_id") == current_customer_id]

    payments, payment_error = _safe_get_json(f"{PAY_SERVICE_URL}/payments/")
    shipments, shipment_error = _safe_get_json(f"{SHIP_SERVICE_URL}/shipments/")

    if isinstance(orders, list):
        payment_map = {payment.get("order_id"): payment.get("status", "UNKNOWN") for payment in payments if isinstance(payment, dict)}
        shipment_map = {shipment.get("order_id"): shipment.get("status", "UNKNOWN") for shipment in shipments if isinstance(shipment, dict)}

        for order in orders:
            order_id = order.get("id")
            order["payment_status"] = payment_map.get(order_id, "N/A")
            order["shipment_status"] = shipment_map.get(order_id, "N/A")

    merged_error = error or fetch_error or payment_error or shipment_error
    return render(
        request,
        "orders.html",
        {
            "orders": orders,
            "error": merged_error,
            "is_customer": is_customer,
            "current_customer_id": current_customer_id,
        },
    )


@login_required
def order_detail(request, order_id):
    role = _get_user_role(request.user) or "customer"
    if role != "staff":
        return redirect("orders")

    error = None
    order = None
    payment = None
    shipment = None
    customer = None

    try:
        order_resp = requests.get(f"{ORDER_SERVICE_URL}/orders/{order_id}/", timeout=5)
        if order_resp.status_code == 200:
            order = order_resp.json()
        else:
            error = f"Order not found (status {order_resp.status_code})"
    except requests.RequestException as exc:
        error = str(exc)

    if order and not error:
        payments, payments_error = _safe_get_json(f"{PAY_SERVICE_URL}/payments/")
        if payments_error:
            error = payments_error
        elif isinstance(payments, list):
            payment = next((row for row in payments if row.get("order_id") == order_id), None)

    if order and not error:
        shipments, shipments_error = _safe_get_json(f"{SHIP_SERVICE_URL}/shipments/")
        if shipments_error:
            error = shipments_error
        elif isinstance(shipments, list):
            shipment = next((row for row in shipments if row.get("order_id") == order_id), None)

    if order and not error:
        customers, customers_error = _safe_get_json(f"{CUSTOMER_SERVICE_URL}/customers/")
        if customers_error:
            error = customers_error
        elif isinstance(customers, list):
            customer = next((row for row in customers if row.get("id") == order.get("customer_id")), None)

    return render(
        request,
        "order_detail.html",
        {
            "error": error,
            "order": order,
            "payment": payment,
            "shipment": shipment,
            "customer": customer,
        },
    )


@login_required
def payment_list(request):
    error = None
    role = _get_user_role(request.user) or "customer"
    is_customer = role == "customer"
    current_customer_id = None

    if is_customer:
        current_customer_id, customer_err = _ensure_customer_for_user(request.user)
        if customer_err:
            error = customer_err

    if request.method == "POST" and not is_customer:
        payload = {
            "order_id": _to_int(request.POST.get("order_id", "0"), 0),
            "status": request.POST.get("status", "PAID"),
        }
        error = _post_json_with_error(f"{PAY_SERVICE_URL}/payments/", payload, "Create payment failed")
        if not error:
            return redirect("payments")

    payments, fetch_error = _safe_get_json(f"{PAY_SERVICE_URL}/payments/")

    if is_customer and isinstance(payments, list):
        orders, orders_error = _safe_get_json(f"{ORDER_SERVICE_URL}/orders/")
        if orders_error and not error:
            error = orders_error

        customer_order_ids = set()
        if isinstance(orders, list):
            customer_order_ids = {
                order.get("id")
                for order in orders
                if isinstance(order, dict) and order.get("customer_id") == current_customer_id
            }

        payments = [
            payment
            for payment in payments
            if isinstance(payment, dict) and payment.get("order_id") in customer_order_ids
        ]

    return render(
        request,
        "payments.html",
        {
            "payments": payments,
            "error": error or fetch_error,
            "is_customer": is_customer,
        },
    )


@login_required
def payment_detail(request, payment_id):
    role = _get_user_role(request.user) or "customer"
    if role != "staff":
        return redirect("payments")

    error = None
    payment = None
    order = None
    customer = None
    shipment = None

    try:
        payment_resp = requests.get(f"{PAY_SERVICE_URL}/payments/{payment_id}/", timeout=5)
        if payment_resp.status_code == 200:
            payment = payment_resp.json()
        else:
            error = f"Payment not found (status {payment_resp.status_code})"
    except requests.RequestException as exc:
        error = str(exc)

    if payment and not error:
        order_id = payment.get("order_id")
        try:
            order_resp = requests.get(f"{ORDER_SERVICE_URL}/orders/{order_id}/", timeout=5)
            if order_resp.status_code == 200:
                order = order_resp.json()
            else:
                error = f"Order not found (status {order_resp.status_code})"
        except requests.RequestException as exc:
            error = str(exc)

    if order and not error:
        customers, customers_error = _safe_get_json(f"{CUSTOMER_SERVICE_URL}/customers/")
        if customers_error:
            error = customers_error
        elif isinstance(customers, list):
            customer = next((row for row in customers if row.get("id") == order.get("customer_id")), None)

    if payment and not error:
        shipments, shipments_error = _safe_get_json(f"{SHIP_SERVICE_URL}/shipments/")
        if shipments_error:
            error = shipments_error
        elif isinstance(shipments, list):
            shipment = next((row for row in shipments if row.get("order_id") == payment.get("order_id")), None)

    return render(
        request,
        "payment_detail.html",
        {
            "error": error,
            "payment": payment,
            "order": order,
            "customer": customer,
            "shipment": shipment,
        },
    )


@login_required
def shipment_list(request):
    error = None
    if request.method == "POST":
        payload = {
            "order_id": _to_int(request.POST.get("order_id", "0"), 0),
            "status": request.POST.get("status", "SHIPPED"),
        }
        error = _post_json_with_error(f"{SHIP_SERVICE_URL}/shipments/", payload, "Create shipment failed")
        if not error:
            return redirect("shipments")

    shipments, fetch_error = _safe_get_json(f"{SHIP_SERVICE_URL}/shipments/")
    return render(request, "shipments.html", {"shipments": shipments, "error": error or fetch_error})


@login_required
def rating_list(request):
    error = None
    if request.method == "POST":
        payload = {
            "customer_id": _to_int(request.POST.get("customer_id", "0"), 0),
            "book_id": _to_int(request.POST.get("book_id", "0"), 0),
            "rating": _to_int(request.POST.get("rating", "5"), 5),
            "comment": request.POST.get("comment", ""),
        }
        error = _post_json_with_error(f"{COMMENT_RATE_SERVICE_URL}/ratings/", payload, "Create rating failed")
        if not error:
            return redirect("ratings")

    ratings, fetch_error = _safe_get_json(f"{COMMENT_RATE_SERVICE_URL}/ratings/")
    return render(request, "ratings.html", {"ratings": ratings, "error": error or fetch_error})


@login_required
def recommendation_page(request):
    customer_id = request.GET.get("customer_id", "1")
    recommendations = []
    recommended_books = []
    strategy = ""
    error = None
    try:
        response = requests.get(f"{RECOMMENDER_AI_SERVICE_URL}/recommendations/{customer_id}/", timeout=5)
        if response.status_code == 200:
            payload = response.json()
            recommendations = payload.get("recommended_books", [])
            strategy = payload.get("strategy", "")

            books_resp = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=5)
            if books_resp.status_code == 200:
                all_books = books_resp.json()
                book_map = {book.get("id"): book for book in all_books}
                recommended_books = [book_map[book_id] for book_id in recommendations if book_id in book_map]
        else:
            error = f"Recommendation failed with status {response.status_code}"
    except requests.RequestException as exc:
        error = str(exc)

    return render(
        request,
        "recommendations.html",
        {
            "recommendations": recommendations,
            "recommended_books": recommended_books,
            "customer_id": customer_id,
            "strategy": strategy,
            "error": error,
        },
    )