import pytest


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_security_headers(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


def test_login_failures_are_rate_limited(client):
    payload = {"email": "ratelimit@campus.local", "password": "wrong-password"}
    for _ in range(5):
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401

    blocked = client.post("/api/v1/auth/login", json=payload)
    assert blocked.status_code == 429


def test_production_rejects_weak_token_secret(monkeypatch):
    from app.core.config import settings, validate_production_settings

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "token_secret", "change-me")
    with pytest.raises(RuntimeError):
        validate_production_settings()

    monkeypatch.setattr(settings, "token_secret", "x" * 64)
    validate_production_settings()


def test_request_id_is_generated_and_propagated(client):
    generated = client.get("/health")
    assert generated.headers["x-request-id"]

    supplied = client.get("/health", headers={"X-Request-ID": "test-request-123"})
    assert supplied.headers["x-request-id"] == "test-request-123"

    rejected = client.get("/health", headers={"X-Request-ID": "bad id with spaces"})
    assert rejected.headers["x-request-id"] != "bad id with spaces"


def test_catalog_and_listings(client):
    catalog = client.get("/api/v1/textbooks", params={"q": "机器学习"})
    assert catalog.status_code == 200
    assert len(catalog.json()) == 1

    listings = client.get("/api/v1/listings")
    assert listings.status_code == 200
    assert len(listings.json()) >= 4


def test_price_estimate_has_range_and_explanation(client):
    response = client.post(
        "/api/v1/pricing/estimate",
        json={
            "new_price": 88,
            "condition_grade": 8,
            "category": "专业课",
            "demand_factor": 1.2,
            "has_notes": True,
            "edition_current": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["low_price"] <= body["suggested_price"] <= body["high_price"]
    assert body["factors"]["condition"] > 0
    assert "合成" in body["disclaimer"]


def test_recommendation_returns_available_books(client):
    listings = client.get("/api/v1/listings").json()
    seed_textbook_id = listings[0]["textbook_id"]
    response = client.get(
        "/api/v1/recommendations",
        params={"seed_textbook_id": seed_textbook_id, "limit": 4},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "content_popularity_baseline"
    assert 1 <= len(body["items"]) <= 4


def test_register_and_create_listing(client, student_headers):
    catalog = client.get("/api/v1/textbooks", params={"q": "Python"}).json()[0]
    response = client.post(
        "/api/v1/listings",
        headers=student_headers,
        json={
            "textbook_id": catalog["id"],
            "condition_grade": 9,
            "asking_price": 32.0,
            "note": "测试发布",
        },
    )
    assert response.status_code == 201
    assert response.json()["textbook_title"] == catalog["title"]


def test_order_idempotency_and_state_machine(client, student_headers):
    listings = client.get("/api/v1/listings").json()
    listing = next(item for item in listings if item["seller_name"] == "顾同学")
    payload = {"listing_id": listing["id"], "idempotency_key": "test-order-idem-0001"}

    first = client.post("/api/v1/orders", headers=student_headers, json=payload)
    second = client.post("/api/v1/orders", headers=student_headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    order_id = first.json()["id"]
    paid = client.post(f"/api/v1/orders/{order_id}/pay", headers=student_headers)
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"

    completed = client.post(f"/api/v1/orders/{order_id}/complete", headers=student_headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    repeated = client.post(f"/api/v1/orders/{order_id}/complete", headers=student_headers)
    assert repeated.status_code == 409


def test_cancelled_order_allows_a_new_order(client, student_headers):
    me = client.get("/api/v1/auth/me", headers=student_headers).json()
    listing = next(
        item
        for item in client.get("/api/v1/listings").json()
        if item["seller_id"] != me["id"]
    )
    payload = {"listing_id": listing["id"], "idempotency_key": "test-cancel-order-0001"}

    first = client.post("/api/v1/orders", headers=student_headers, json=payload)
    assert first.status_code == 201
    cancelled = client.post(
        f"/api/v1/orders/{first.json()['id']}/cancel", headers=student_headers
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    second = client.post(
        "/api/v1/orders",
        headers=student_headers,
        json={"listing_id": listing["id"], "idempotency_key": "test-cancel-order-0002"},
    )
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]


def test_refunded_order_allows_a_new_order(client, student_headers, admin_headers):
    me = client.get("/api/v1/auth/me", headers=student_headers).json()
    listing = next(
        item
        for item in client.get("/api/v1/listings").json()
        if item["seller_id"] != me["id"]
    )
    created = client.post(
        "/api/v1/orders",
        headers=student_headers,
        json={"listing_id": listing["id"], "idempotency_key": "test-refund-order-0001"},
    )
    assert created.status_code == 201
    order_id = created.json()["id"]

    paid = client.post(f"/api/v1/orders/{order_id}/pay", headers=student_headers)
    assert paid.status_code == 200

    refunded = client.post(
        f"/api/v1/admin/orders/{order_id}/refund",
        headers=admin_headers,
        json={"reason": "测试退款"},
    )
    assert refunded.status_code == 200
    assert refunded.json()["status"] == "refunded"

    replacement = client.post(
        "/api/v1/orders",
        headers=student_headers,
        json={"listing_id": listing["id"], "idempotency_key": "test-refund-order-0002"},
    )
    assert replacement.status_code == 201
    assert replacement.json()["id"] != order_id


def test_admin_can_moderate_listings(client, student_headers, admin_headers):
    forbidden = client.get("/api/v1/admin/listings", headers=student_headers)
    assert forbidden.status_code == 403

    textbook = client.get("/api/v1/textbooks", params={"q": "Python"}).json()[0]
    created = client.post(
        "/api/v1/listings",
        headers=student_headers,
        json={
            "textbook_id": textbook["id"],
            "condition_grade": 9,
            "asking_price": 30.0,
            "note": "管理员审核测试",
        },
    )
    assert created.status_code == 201
    listing_id = created.json()["id"]

    listing_rows = client.get(
        "/api/v1/admin/listings",
        headers=admin_headers,
        params={"status": "active"},
    ).json()
    assert any(row["id"] == listing_id for row in listing_rows)

    removed = client.patch(
        f"/api/v1/admin/listings/{listing_id}",
        headers=admin_headers,
        json={"status": "removed", "reason": "测试下架"},
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "removed"
    assert client.get(f"/api/v1/listings/{listing_id}").json()["status"] == "removed"

    restored = client.patch(
        f"/api/v1/admin/listings/{listing_id}",
        headers=admin_headers,
        json={"status": "active", "reason": "测试恢复"},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_admin_can_list_and_refund_orders(client, student_headers, admin_headers):
    forbidden = client.get("/api/v1/admin/orders", headers=student_headers)
    assert forbidden.status_code == 403

    me = client.get("/api/v1/auth/me", headers=student_headers).json()
    listing = next(
        item
        for item in client.get("/api/v1/listings").json()
        if item["seller_id"] != me["id"]
    )
    created = client.post(
        "/api/v1/orders",
        headers=student_headers,
        json={"listing_id": listing["id"], "idempotency_key": "test-admin-list-0001"},
    )
    assert created.status_code == 201
    order_id = created.json()["id"]
    assert (
        client.post(f"/api/v1/orders/{order_id}/pay", headers=student_headers).status_code
        == 200
    )

    paid_orders = client.get(
        "/api/v1/admin/orders",
        headers=admin_headers,
        params={"status": "paid"},
    ).json()
    target = next(row for row in paid_orders if row["id"] == order_id)
    assert target["buyer_name"]
    assert target["seller_name"]
    assert target["textbook_title"]

    refunded = client.post(
        f"/api/v1/admin/orders/{order_id}/refund",
        headers=admin_headers,
        json={"reason": "管理员列表退款测试"},
    )
    assert refunded.status_code == 200
    assert refunded.json()["status"] == "refunded"


def test_admin_metrics_requires_admin(client, student_headers, admin_headers):
    forbidden = client.get("/api/v1/admin/metrics", headers=student_headers)
    assert forbidden.status_code == 403

    allowed = client.get("/api/v1/admin/metrics", headers=admin_headers)
    assert allowed.status_code == 200
    assert allowed.json()["textbooks"] >= 6


ONE_PIXEL_PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000D49444154789C6360000000020001E221BC330000000049454E44AE426082"
)


def test_image_upload_and_static_serving(client, student_headers):
    response = client.post(
        "/api/v1/listings/images",
        headers=student_headers,
        files={"file": ("cover.png", ONE_PIXEL_PNG, "image/png")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["image_url"].startswith("/media/listings/")
    assert body["content_type"] == "image/png"

    served = client.get(body["image_url"])
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.content == ONE_PIXEL_PNG


def test_image_upload_rejects_non_images(client, student_headers):
    response = client.post(
        "/api/v1/listings/images",
        headers=student_headers,
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415


def test_image_upload_requires_authentication(client):
    response = client.post(
        "/api/v1/listings/images",
        files={"file": ("cover.png", ONE_PIXEL_PNG, "image/png")},
    )
    assert response.status_code == 401
