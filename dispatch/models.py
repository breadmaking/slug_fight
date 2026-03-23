from django.db import models

from api.models import Detection


class MissionState(models.TextChoices):
    PENDING = "pending"
    LAUNCHING = "launching"
    NAVIGATING = "navigating"
    HOVERING = "hovering"
    DROPPING = "dropping"
    RETURNING = "returning"
    LANDING = "landing"
    COMPLETE = "complete"
    FAILED = "failed"
    ABORTED = "aborted"


TERMINAL_STATES = {MissionState.COMPLETE, MissionState.FAILED, MissionState.ABORTED}


class Mission(models.Model):
    detection = models.OneToOneField(
        Detection, on_delete=models.CASCADE, related_name="mission"
    )
    state = models.CharField(
        max_length=16,
        choices=MissionState.choices,
        default=MissionState.PENDING,
    )
    failure_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Mission #{self.pk} [{self.state}]"

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
