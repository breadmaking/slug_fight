import logging

from api.models import Detection
from dispatch.drone import DroneInterface
from dispatch.models import TERMINAL_STATES, Mission, MissionState

logger = logging.getLogger(__name__)

FLIGHT_ALTITUDE = 5.0
LOW_BATTERY_THRESHOLD = 30.0

STATE_SEQUENCE = [
    MissionState.PENDING,
    MissionState.LAUNCHING,
    MissionState.NAVIGATING,
    MissionState.HOVERING,
    MissionState.DROPPING,
    MissionState.RETURNING,
    MissionState.LANDING,
    MissionState.COMPLETE,
]


class Coordinator:
    def __init__(self, drone: DroneInterface) -> None:
        self.drone = drone

    def tick(self) -> None:
        active = Mission.objects.exclude(state__in=TERMINAL_STATES).first()

        if active is None:
            active = self._claim_next_detection()

        if active is None:
            return

        self._advance(active)

    def _claim_next_detection(self) -> Mission | None:
        unclaimed = (
            Detection.objects.filter(mission__isnull=True)
            .order_by("created_at")
            .first()
        )
        if unclaimed is None:
            return None

        mission = Mission.objects.create(detection=unclaimed)
        logger.info("Created %s for detection %s", mission, unclaimed)
        return mission

    def _advance(self, mission: Mission) -> None:
        status = self.drone.get_status()

        if status.battery < LOW_BATTERY_THRESHOLD:
            self._abort(mission, f"Low battery: {status.battery}%")
            return

        match mission.state:
            case MissionState.PENDING:
                self._transition(mission, MissionState.LAUNCHING)
                self.drone.arm_and_takeoff(FLIGHT_ALTITUDE)

            case MissionState.LAUNCHING:
                if status.alt >= FLIGHT_ALTITUDE * 0.9:
                    det = mission.detection
                    self.drone.goto(det.lat, det.lon, FLIGHT_ALTITUDE)
                    self._transition(mission, MissionState.NAVIGATING)

            case MissionState.NAVIGATING:
                if self.drone.has_arrived():
                    self._transition(mission, MissionState.HOVERING)

            case MissionState.HOVERING:
                self.drone.drop_payload()
                self._transition(mission, MissionState.DROPPING)

            case MissionState.DROPPING:
                self.drone.return_to_launch()
                self._transition(mission, MissionState.RETURNING)

            case MissionState.RETURNING:
                if self.drone.has_arrived():
                    self.drone.land()
                    self._transition(mission, MissionState.LANDING)

            case MissionState.LANDING:
                if self.drone.has_landed():
                    self.drone.disarm()
                    self._transition(mission, MissionState.COMPLETE)

    def _transition(self, mission: Mission, new_state: MissionState) -> None:
        old = mission.state
        mission.state = new_state
        mission.save(update_fields=["state", "updated_at"])
        logger.info("%s: %s → %s", mission, old, new_state)

    def _abort(self, mission: Mission, reason: str) -> None:
        logger.warning("Aborting %s: %s", mission, reason)
        self.drone.return_to_launch()
        mission.state = MissionState.ABORTED
        mission.failure_reason = reason
        mission.save(update_fields=["state", "failure_reason", "updated_at"])
