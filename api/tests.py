import pytest
from django.test import Client

from api.models import Detection


@pytest.mark.django_db
class TestDetectionAPI:
    def test_create_detection(self, client: Client) -> None:
        resp = client.post(
            "/api/detections/",
            {"lat": 51.5074, "lon": -0.1278, "confidence": 0.94, "source": "sim"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["lat"] == 51.5074
        assert data["lon"] == -0.1278
        assert data["confidence"] == 0.94
        assert data["source"] == "sim"
        assert "id" in data
        assert "created_at" in data
        assert Detection.objects.count() == 1

    def test_create_detection_default_source(self, client: Client) -> None:
        resp = client.post(
            "/api/detections/",
            {"lat": 51.0, "lon": -0.1, "confidence": 0.9},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["source"] == "unknown"

    def test_create_detection_missing_fields(self, client: Client) -> None:
        resp = client.post(
            "/api/detections/",
            {"lat": 51.0},
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_list_detections_empty(self, client: Client) -> None:
        resp = client.get("/api/detections/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_detections_ordered_newest_first(self, client: Client) -> None:
        d1 = Detection.objects.create(lat=1.0, lon=1.0, confidence=0.9)
        d2 = Detection.objects.create(lat=2.0, lon=2.0, confidence=0.8)
        resp = client.get("/api/detections/")
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == d2.id
        assert data[1]["id"] == d1.id
