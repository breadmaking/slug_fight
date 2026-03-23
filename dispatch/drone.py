from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DroneStatus:
    lat: float
    lon: float
    alt: float
    battery: float
    is_armed: bool


class DroneInterface(ABC):
    @abstractmethod
    def get_status(self) -> DroneStatus: ...

    @abstractmethod
    def arm_and_takeoff(self, altitude: float) -> None: ...

    @abstractmethod
    def goto(self, lat: float, lon: float, alt: float) -> None: ...

    @abstractmethod
    def has_arrived(self) -> bool: ...

    @abstractmethod
    def drop_payload(self) -> None: ...

    @abstractmethod
    def return_to_launch(self) -> None: ...

    @abstractmethod
    def land(self) -> None: ...

    @abstractmethod
    def has_landed(self) -> bool: ...

    @abstractmethod
    def disarm(self) -> None: ...
