from collections import defaultdict

import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response


BOOK_SERVICE_URL = "http://book-service:8000"
RATING_SERVICE_URL = "http://comment-rate-service:8000"
MAX_RECOMMENDATIONS = 5


def _safe_get_json(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json(), None
        return [], f"GET {url} failed with status {response.status_code}"
    except requests.RequestException as exc:
        return [], str(exc)


@api_view(["GET"])
def get_recommendation(request, customer_id):
    books, books_error = _safe_get_json(f"{BOOK_SERVICE_URL}/books/")
    ratings, ratings_error = _safe_get_json(f"{RATING_SERVICE_URL}/ratings/")

    if books_error:
        return Response({"recommended_books": [], "error": books_error}, status=503)
    if ratings_error:
        return Response({"recommended_books": [], "error": ratings_error}, status=503)

    available_book_ids = {book.get("id") for book in books if book.get("id") is not None}
    ratings = [r for r in ratings if r.get("book_id") in available_book_ids]

    by_customer = defaultdict(list)
    for item in ratings:
        by_customer[item.get("customer_id")].append(item)

    target_ratings = by_customer.get(customer_id, [])
    target_rated_books = {item.get("book_id") for item in target_ratings}
    liked_books = {item.get("book_id") for item in target_ratings if int(item.get("rating", 0)) >= 4}

    candidate_scores = defaultdict(float)
    strategy = "popular_fallback"

    if liked_books:
        strategy = "collaborative"
        similar_customers = {
            cid
            for cid, items in by_customer.items()
            if cid != customer_id and any(i.get("book_id") in liked_books and int(i.get("rating", 0)) >= 4 for i in items)
        }

        for cid in similar_customers:
            for item in by_customer[cid]:
                book_id = item.get("book_id")
                rating_value = int(item.get("rating", 0))
                if book_id in target_rated_books or rating_value < 4:
                    continue
                candidate_scores[book_id] += rating_value

    if not candidate_scores:
        for item in ratings:
            book_id = item.get("book_id")
            rating_value = int(item.get("rating", 0))
            if book_id in target_rated_books or rating_value <= 0:
                continue
            candidate_scores[book_id] += rating_value

    ranked_ids = [
        book_id
        for book_id, _ in sorted(candidate_scores.items(), key=lambda x: (-x[1], x[0]))
        if book_id in available_book_ids
    ]

    if not ranked_ids:
        strategy = "catalog_fallback"
        ranked_ids = sorted(available_book_ids)

    return Response(
        {
            "customer_id": customer_id,
            "recommended_books": ranked_ids[:MAX_RECOMMENDATIONS],
            "strategy": strategy,
        }
    )
