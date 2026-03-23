from django.db import models


class Detection(models.Model):
    lat = models.FloatField()
    lon = models.FloatField()
    confidence = models.FloatField()
    source = models.CharField(max_length=32, default="unknown")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Detection({self.lat:.5f}, {self.lon:.5f}, {self.confidence:.0%})"
