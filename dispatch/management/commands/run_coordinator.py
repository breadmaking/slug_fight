import logging
import time

from django.core.management.base import BaseCommand

from dispatch.coordinator import Coordinator
from dispatch.dronekit_drone import DronekitDrone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Connect to ArduPilot and run the coordinator tick loop."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--connection",
            default="tcp:127.0.0.1:5760",
            help="MAVLink connection string (default: tcp:127.0.0.1:5760)",
        )
        parser.add_argument(
            "--tick-interval",
            type=float,
            default=1.0,
            help="Seconds between coordinator ticks (default: 1.0)",
        )

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )

        connection = options["connection"]
        interval = options["tick_interval"]

        self.stdout.write(f"Connecting to {connection} ...")
        drone = DronekitDrone(connection_string=connection)
        coordinator = Coordinator(drone)
        self.stdout.write(self.style.SUCCESS("Connected. Coordinator running."))
        self.stdout.write(f"Tick interval: {interval}s — Ctrl-C to stop.")

        from dispatch.models import TERMINAL_STATES, Mission

        try:
            while True:
                active = Mission.objects.exclude(
                    state__in=TERMINAL_STATES
                ).first()
                coordinator.tick()
                if active:
                    active.refresh_from_db()
                    status = drone.get_status()
                    target = drone._target
                    dist = ""
                    if target:
                        from dispatch.dronekit_drone import _haversine_m

                        horiz = _haversine_m(
                            status.lat, status.lon, target[0], target[1]
                        )
                        vert = abs(status.alt - target[2])
                        dist = f" dist={horiz:.1f}m vert={vert:.1f}m"
                    self.stdout.write(
                        f"[{active.state}] alt={status.alt:.1f}m "
                        f"bat={status.battery:.0f}% "
                        f"pos=({status.lat:.6f},{status.lon:.6f})"
                        f"{dist}"
                    )
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("\nShutting down ...")
        finally:
            drone.close()
            self.stdout.write(self.style.SUCCESS("Done."))
