from datetime import datetime

from ninja import NinjaAPI, Schema

from api.models import Detection

api = NinjaAPI(urls_namespace="api")


class DetectionIn(Schema):
    lat: float
    lon: float
    confidence: float
    source: str = "unknown"


class DetectionOut(Schema):
    id: int
    lat: float
    lon: float
    confidence: float
    source: str
    created_at: datetime


@api.post("/detections/", response=DetectionOut)
def create_detection(request: object, payload: DetectionIn) -> Detection:
    return Detection.objects.create(**payload.dict())


@api.get("/detections/", response=list[DetectionOut])
def list_detections(request: object) -> list[Detection]:
    return list(Detection.objects.all()[:50])
