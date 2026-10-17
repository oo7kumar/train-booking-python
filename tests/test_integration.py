"""Integration tests using real PostgreSQL and Redis."""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import cache, db
from app.main import app


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") or not os.getenv("REDIS_URL"),
    reason="Integration tests require DATABASE_URL and REDIS_URL",
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_checks_postgres_and_redis(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "postgres": True,
        "redis": True,
    }


def test_search_uses_redis_cache(client):
    train = db.one(
        "SELECT departs_at::date AS travel_date FROM trains WHERE id = %s",
        (1,),
    )
    travel_date = train["travel_date"].isoformat()
    cache_key = f"search:CSMT:NDLS:{travel_date}"

    # Ensure the first request is a cache miss.
    cache.client().delete(cache_key)

    try:
        first = client.get(
            "/search",
            params={
                "origin": "CSMT",
                "destination": "NDLS",
                "date": travel_date,
            },
        )

        assert first.status_code == 200
        assert first.json()["cached"] is False
        assert any(
            train_result["train_id"] == 1
            for train_result in first.json()["trains"]
        )

        second = client.get(
            "/search",
            params={
                "origin": "CSMT",
                "destination": "NDLS",
                "date": travel_date,
            },
        )

        assert second.status_code == 200
        assert second.json()["cached"] is True
    finally:
        cache.client().delete(cache_key)


def test_booking_is_saved_and_can_be_retrieved(client):
    passenger = f"Integration Test {uuid4().hex[:12]}"
    pnr = None

    try:
        response = client.post(
            "/bookings",
            json={
                "train_id": 1,
                "passenger": passenger,
                "travel_class": "SL",
                "origin": "CSMT",
                "destination": "NSK",
                "seats": 1,
            },
        )

        assert response.status_code == 201, response.text

        booking_data = response.json()
        pnr = booking_data["pnr"]

        assert booking_data["passenger"] == passenger
        assert booking_data["status"] == "CONFIRMED"
        assert booking_data["seats"] == 1

        retrieved = client.get(f"/bookings/{pnr}")

        assert retrieved.status_code == 200
        assert retrieved.json()["pnr"] == pnr
        assert retrieved.json()["passenger"] == passenger
        assert retrieved.json()["status"] == "CONFIRMED"

    finally:
        # Cancel the test booking so it doesn't consume a seat.
        if pnr:
            cleanup = client.delete(f"/bookings/{pnr}")
            assert cleanup.status_code == 200, cleanup.text
