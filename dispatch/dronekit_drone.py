import collections
import collections.abc
import logging
import math
import time
from collections.abc import Callable

# dronekit references collections.MutableMapping which was removed in 3.10+
for _attr in ("MutableMapping", "MutableSequence", "Iterator"):
    if not hasattr(collections, _attr):
        setattr(collections, _attr, getattr(collections.abc, _attr))

from dronekit import LocationGlobalRelative, Vehicle, VehicleMode, connect  # noqa: E402

from dispatch.drone import DroneInterface, DroneStatus  # noqa: E402

logger = logging.getLogger(__name__)

ARRIVAL_THRESHOLD_M = 2.0
ARM_TIMEOUT_S = 30
MODE_TIMEOUT_S = 10


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class DronekitDrone(DroneInterface):
    def __init__(
        self,
        connection_string: str = "tcp:127.0.0.1:5760",
        payload_fn: Callable[[], None] | None = None,
    ) -> None:
        logger.info("Connecting to vehicle at %s", connection_string)
        self._vehicle: Vehicle = connect(connection_string, wait_ready=True)
        logger.info("Connected: %s", self._vehicle.version)
        self._target: tuple[float, float, float] | None = None
        self._home_lat: float = 0.0
        self._home_lon: float = 0.0
        self._payload_fn = payload_fn

    def get_status(self) -> DroneStatus:
        loc = self._vehicle.location.global_relative_frame
        batt = self._vehicle.battery
        return DroneStatus(
            lat=loc.lat,
            lon=loc.lon,
            alt=loc.alt,
            battery=batt.level if batt.level is not None else 0.0,
            is_armed=self._vehicle.armed,
        )

    def arm_and_takeoff(self, altitude: float) -> None:
        loc = self._vehicle.location.global_relative_frame
        self._home_lat = loc.lat
        self._home_lon = loc.lon

        self._set_mode("GUIDED")

        self._vehicle.armed = True
        deadline = time.monotonic() + ARM_TIMEOUT_S
        while not self._vehicle.armed:
            if time.monotonic() > deadline:
                raise TimeoutError("Vehicle failed to arm within timeout")
            time.sleep(0.5)
        logger.info("Armed")

        self._vehicle.simple_takeoff(altitude)
        logger.info("Takeoff to %.1fm commanded", altitude)

    def goto(self, lat: float, lon: float, alt: float) -> None:
        self._target = (lat, lon, alt)
        self._vehicle.simple_goto(LocationGlobalRelative(lat, lon, alt))
        logger.info("Goto (%.6f, %.6f, %.1f)", lat, lon, alt)

    def has_arrived(self) -> bool:
        if self._target is None:
            return False
        loc = self._vehicle.location.global_relative_frame
        horiz = _haversine_m(loc.lat, loc.lon, self._target[0], self._target[1])
        vert = abs(loc.alt - self._target[2])
        arrived = horiz < ARRIVAL_THRESHOLD_M and vert < 1.0
        if arrived:
            logger.info("Arrived at target (%.1fm horiz, %.1fm vert)", horiz, vert)
        return arrived

    def drop_payload(self) -> None:
        if self._payload_fn is not None:
            self._payload_fn()
        logger.info("Payload dropped")

    def return_to_launch(self) -> None:
        alt = self._vehicle.location.global_relative_frame.alt
        self._target = (self._home_lat, self._home_lon, alt)
        self._vehicle.simple_goto(
            LocationGlobalRelative(self._home_lat, self._home_lon, self._target[2])
        )
        logger.info("Returning to launch (%.6f, %.6f)", self._home_lat, self._home_lon)

    def land(self) -> None:
        self._set_mode("LAND")
        logger.info("Land commanded")

    def has_landed(self) -> bool:
        return bool(self._vehicle.location.global_relative_frame.alt < 0.3)

    def disarm(self) -> None:
        self._vehicle.armed = False
        logger.info("Disarm commanded")

    def close(self) -> None:
        self._vehicle.close()
        logger.info("Vehicle connection closed")

    def _set_mode(self, mode_name: str) -> None:
        self._vehicle.mode = VehicleMode(mode_name)
        deadline = time.monotonic() + MODE_TIMEOUT_S
        while self._vehicle.mode.name != mode_name:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Failed to enter {mode_name} mode within timeout")
            time.sleep(0.5)
        logger.info("Mode: %s", mode_name)
