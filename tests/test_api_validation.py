from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_rejects_missing_origin():
    response = client.get(
        "/search",
        params={"destination": "DEL", "date": "2026-12-01"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "origin and destination are required"


def test_search_rejects_missing_destination():
    response = client.get(
        "/search",
        params={"origin": "MUM", "date": "2026-12-01"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "origin and destination are required"


def test_search_rejects_same_origin_and_destination():
    response = client.get(
        "/search",
        params={
            "origin": "MUM",
            "destination": "MUM",
            "date": "2026-12-01",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "origin and destination are the same station"
    )


def test_search_rejects_missing_date():
    response = client.get(
        "/search",
        params={"origin": "MUM", "destination": "DEL"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "date is required, as YYYY-MM-DD"


def test_search_rejects_invalid_date():
    response = client.get(
        "/search",
        params={
            "origin": "MUM",
            "destination": "DEL",
            "date": "not-a-date",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "date must be YYYY-MM-DD"
