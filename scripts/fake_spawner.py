"""Fire fake slug detections near SITL home on a timer."""

import argparse
import random
import time

import httpx

SITL_HOME_LAT = -35.3632621
SITL_HOME_LON = 149.1652374
SPREAD_M = 30
M_PER_DEG_LAT = 111_320
M_PER_DEG_LON = 111_320 * 0.8171  # cos(-35.36°)


def random_detection() -> dict[str, float | str]:
    dlat = random.uniform(-SPREAD_M, SPREAD_M) / M_PER_DEG_LAT
    dlon = random.uniform(-SPREAD_M, SPREAD_M) / M_PER_DEG_LON
    return {
        "lat": SITL_HOME_LAT + dlat,
        "lon": SITL_HOME_LON + dlon,
        "confidence": round(random.uniform(0.70, 0.99), 2),
        "source": "fake_spawner",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api",
        default="http://localhost:8000/api/detections/",
        help="Detection API endpoint",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Seconds between detections (default: 60)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Number of detections to send (0 = unlimited)",
    )
    args = parser.parse_args()

    client = httpx.Client()
    sent = 0

    print(f"Spawning detections → {args.api}")
    print(f"Interval: {args.interval}s | Count: {args.count or 'unlimited'}")

    try:
        while args.count == 0 or sent < args.count:
            det = random_detection()
            resp = client.post(args.api, json=det)
            sent += 1
            print(
                f"[{sent}] ({det['lat']:.6f}, {det['lon']:.6f}) "
                f"conf={det['confidence']} → {resp.status_code}"
            )
            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\nStopped after {sent} detections.")


if __name__ == "__main__":
    main()
