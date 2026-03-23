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
def create_detection(request, payload: DetectionIn):
    detection = Detection.objects.create(**payload.dict())
    return detection


@api.get("/detections/", response=list[DetectionOut])
def list_detections(request):
    return Detection.objects.all()[:50]
