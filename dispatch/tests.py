import pytest

from api.models import Detection
from dispatch.coordinator import LOW_BATTERY_THRESHOLD, Coordinator
from dispatch.drone import DroneInterface, DroneStatus
from dispatch.models import Mission, MissionState


class StubDrone(DroneInterface):
    def __init__(self) -> None:
        self.lat = 0.0
        self.lon = 0.0
        self.alt = 0.0
        self.battery = 100.0
        self.is_armed = False
        self._arrived = False
        self._landed = True
        self.payload_dropped = False
        self.rtl_called = False

    def get_status(self) -> DroneStatus:
        return DroneStatus(
            lat=self.lat,
            lon=self.lon,
            alt=self.alt,
            battery=self.battery,
            is_armed=self.is_armed,
        )

    def arm_and_takeoff(self, altitude: float) -> None:
        self.is_armed = True
        self.alt = altitude
        self._landed = False

    def goto(self, lat: float, lon: float, alt: float) -> None:
        self.lat = lat
        self.lon = lon
        self.alt = alt

    def has_arrived(self) -> bool:
        return self._arrived

    def drop_payload(self) -> None:
        self.payload_dropped = True

    def return_to_launch(self) -> None:
        self.rtl_called = True
        self.lat = 0.0
        self.lon = 0.0

    def land(self) -> None:
        self.alt = 0.0
        self._landed = True

    def has_landed(self) -> bool:
        return self._landed

    def disarm(self) -> None:
        self.is_armed = False


@pytest.mark.django_db
class TestCoordinator:
    def _make_detection(self, **kwargs: float | str) -> Detection:
        defaults: dict[str, float | str] = {
            "lat": 51.5074,
            "lon": -0.1278,
            "confidence": 0.94,
            "source": "test",
        }
        defaults.update(kwargs)
        return Detection.objects.create(**defaults)

    def test_no_detections_does_nothing(self) -> None:
        drone = StubDrone()
        coord = Coordinator(drone)
        coord.tick()
        assert Mission.objects.count() == 0

    def test_claims_detection_and_starts_mission(self) -> None:
        self._make_detection()
        drone = StubDrone()
        coord = Coordinator(drone)
        coord.tick()

        assert Mission.objects.count() == 1
        mission = Mission.objects.first()
        assert mission is not None
        assert mission.state == MissionState.LAUNCHING
        assert drone.is_armed

    def test_full_mission_cycle(self) -> None:
        self._make_detection()
        drone = StubDrone()
        coord = Coordinator(drone)

        # PENDING → LAUNCHING (arm + takeoff)
        coord.tick()
        mission = Mission.objects.first()
        assert mission is not None
        assert mission.state == MissionState.LAUNCHING

        # LAUNCHING → NAVIGATING (altitude reached)
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.NAVIGATING

        # NAVIGATING — not arrived yet
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.NAVIGATING

        # NAVIGATING → HOVERING
        drone._arrived = True
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.HOVERING

        # HOVERING → DROPPING
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.DROPPING
        assert drone.payload_dropped

        # DROPPING → RETURNING
        drone._arrived = False
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.RETURNING
        assert drone.rtl_called

        # RETURNING — not arrived yet
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.RETURNING

        # RETURNING → LANDING
        drone._arrived = True
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.LANDING

        # LANDING → COMPLETE
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.COMPLETE
        assert not drone.is_armed

    def test_duplicate_detection_not_claimed(self) -> None:
        self._make_detection()
        drone = StubDrone()
        coord = Coordinator(drone)

        coord.tick()
        assert Mission.objects.count() == 1

        coord.tick()
        assert Mission.objects.count() == 1

    def test_low_battery_aborts(self) -> None:
        self._make_detection()
        drone = StubDrone()
        drone.battery = LOW_BATTERY_THRESHOLD - 1
        coord = Coordinator(drone)

        coord.tick()
        mission = Mission.objects.first()
        assert mission is not None
        assert mission.state == MissionState.ABORTED
        assert "battery" in mission.failure_reason.lower()
        assert drone.rtl_called

    def test_low_battery_mid_flight_aborts(self) -> None:
        self._make_detection()
        drone = StubDrone()
        coord = Coordinator(drone)

        coord.tick()
        mission = Mission.objects.first()
        assert mission is not None
        assert mission.state == MissionState.LAUNCHING

        drone.battery = LOW_BATTERY_THRESHOLD - 1
        coord.tick()
        mission.refresh_from_db()
        assert mission.state == MissionState.ABORTED

    def test_queues_second_detection(self) -> None:
        self._make_detection(lat=1.0)
        self._make_detection(lat=2.0)
        drone = StubDrone()
        coord = Coordinator(drone)

        coord.tick()
        assert Mission.objects.count() == 1
        first = Mission.objects.first()
        assert first is not None
        assert first.detection.lat == 1.0

        # Complete first mission
        first.state = MissionState.COMPLETE
        first.save()

        coord.tick()
        assert Mission.objects.count() == 2
        second = Mission.objects.order_by("created_at").last()
        assert second is not None
        assert second.detection.lat == 2.0
