# Slug Drone Project — Build Plan

## Overview

An automated garden defence system using a custom-built drone to detect and neutralise slugs with a salt payload. Built iteratively for YouTube documentation. Frame is designed around the payload from day one, running ArduPilot for autonomous flight with a Raspberry Pi companion computer handling all Python logic.

---

## Bill of Materials

| Component | Example Part | Approx Cost |
|---|---|---|
| Flight controller | Matek H743 Slim | £50-70 |
| Frame | 3" or 5" racing frame (to start) | £15-25 |
| Motors x4 | 1400-1800KV brushless (5" build) | £30-50 |
| 4-in-1 ESC | SpeedyBee or similar | £25-40 |
| LiPo battery | 4S 1300-1800mAh | £20-35 |
| Battery charger | ISDT or similar | £20-30 |
| Radio TX | ExpressLRS (e.g. Radiomaster Pocket) | £30-50 |
| Radio RX | ELRS receiver | £10-15 |
| Companion computer | Raspberry Pi Zero 2W | £15 |
| Props, wiring, connectors | Various | £10-15 |
| **Total** | | **£225-345** |

---

## Tech Stack

- Python — drone control, detection, dispatch logic
- Django — control plane, monitoring UI, API layer
- ArduPilot — flight controller firmware (handles all stabilisation)
- `dronekit` — Python MAVLink library for ArduPilot control
- `pymavlink` — lower-level MAVLink if dronekit is insufficient
- YOLOv8 (`ultralytics`) — slug detection model
- OpenCV — camera feed, homography calibration
- PostgreSQL — logging detections, flight events
- Mission Planner / QGroundControl — FC configuration (not Python, one-time setup)

---

## Project Structure

```
slug-drone/
├── control/                  # Django project
│   ├── api/                  # REST endpoints for dispatch
│   ├── dashboard/            # Monitoring UI
│   └── settings/
├── detection/                # Slug detection module
│   ├── model/                # YOLOv8 weights + config
│   ├── calibration/          # Homography camera-to-world mapping
│   └── stream.py             # Camera feed handler
├── drone/                    # Flight control module
│   ├── flight.py             # Takeoff, navigate, land via dronekit
│   ├── payload.py            # Salt release servo control
│   └── dock.py               # Dock return + charging logic
├── dispatch/                 # Coordinator between detection and drone
│   └── coordinator.py
├── hardware/                 # CAD files, wiring diagrams
│   ├── frame/                # 3D printable frame files
│   └── hopper/               # Salt hopper and dock STLs
├── scripts/                  # One-off calibration and test scripts
└── requirements.txt
```

---

## Phases

### Phase 0 — Build & Tune

**Goal:** A physically stable drone that flies reliably under manual control before a single line of Python is written.

**Tasks:**
- Source all components
- Solder ESC, motors, FC
- Flash ArduPilot firmware to FC via Mission Planner
- Configure radio TX/RX (ExpressLRS)
- Initial PID tune — expect a weekend of test flights and crashes
- Achieve stable hover and basic manual navigation
- Set up return-to-home failsafe on radio signal loss

**Notes:**
- This phase has nothing to do with Python — it is hardware and firmware only
- Do not move to Phase 1 until manual flight is solid and failsafes are tested
- Film every crash — this is your first YouTube episode

**Success criteria:** Stable manual hover for 2+ minutes, clean landing, RTH failsafe confirmed working.

**YouTube angle:** "Building a slug-killing drone from scratch — day one. Here's everything that broke."

---

### Phase 1 — Drone Control via Python

**Goal:** Replace manual control with Python scripts via dronekit over MAVLink. Reliable takeoff, navigation to an XY offset, and landing.

**Tasks:**
- Connect Raspberry Pi Zero 2W to FC via UART (MAVLink telemetry port)
- Install `dronekit` on Pi
- Write basic flight script: arm → takeoff → fly forward 50cm → return → land → disarm
- Add battery level monitoring and low-battery abort
- Test repeatedly until autonomous landing is consistent

**Notes:**
- Keep radio TX on hand throughout — override to manual if anything goes wrong
- dronekit's `simple_goto` uses GPS by default; for GPS-free indoor/garden use you will need optical flow or a positioning workaround (covered in Phase 3)
- For early testing, use guided mode with relative position offsets rather than GPS waypoints

**Success criteria:** 10 consecutive clean autonomous takeoff/land cycles with no manual intervention.

**YouTube angle:** "I'm building a slug-killing drone — first autonomous flight."

---

### Phase 2 — Slug Detection (Standalone)

**Goal:** A camera reliably identifies slugs and returns a bounding box with real-world position estimate. No drone involvement yet.

**Tasks:**
- Mount Raspberry Pi + camera to overlook a test bed
- Source or collect slug image dataset (Roboflow has existing datasets)
- Fine-tune YOLOv8n (nano — fastest inference on Pi) on slug images
- Output: class, confidence, pixel bounding box centre
- Log detections to PostgreSQL via Django

**Success criteria:** >85% detection accuracy in outdoor lighting conditions including at night with IR illumination.

**YouTube angle:** "Teaching a computer to spot slugs at 2am."

---

### Phase 3 — Coordinate Translation & Positioning

**Goal:** Convert camera pixel coordinates into drone-navigable real-world XY coordinates, and give the drone a stable position reference without GPS.

**Tasks:**
- Place ArUco markers in the garden bed as a calibration grid
- Use OpenCV to compute a homography matrix (camera pixels → real-world cm)
- Store calibration config per camera mount
- Build a Django API endpoint that accepts a detection event and returns a drone waypoint
- Add optical flow sensor to FC (e.g. Matek 3901-L0X) for GPS-free stable hover
- Test position hold accuracy over the bed

**Notes:**
- This is the most mathematically involved phase
- Optical flow works best on textured surfaces — soil is ideal, concrete is not
- ArUco markers on the dock also enable precise visual landing correction

**Success criteria:** Pixel coordinate translates to real-world position within ±3cm. Drone holds position without GPS.

---

### Phase 4 — Payload Mechanism

**Goal:** A 3D printed salt hopper integrated into the frame that releases a measured dose on command from the Pi.

**Tasks:**
- Design hopper in CAD to fit within the frame footprint without shifting centre of gravity
- 3D print hopper and mount
- Attach micro servo as gate release, wired to Pi GPIO
- Write `drone/payload.py` — GPIO trigger, open gate for N milliseconds, close
- Test salt dispersal pattern from hover height (~30cm above target)
- Tune gate open duration for correct dosage
- Re-tune PIDs with payload weight added

**Notes:**
- Unlike with a Tello, you have full control of the frame design — build the hopper in, don't bolt it on
- Re-weigh and re-tune after adding payload hardware
- This is the episode where you 3D print five versions of the hopper

**Success criteria:** Salt drops within a 5cm radius of target from 30cm altitude.

---

### Phase 5 — Integration & Dispatch Loop

**Goal:** End-to-end automated cycle: detection fires → drone dispatches → drops payload → returns to dock.

**Tasks:**
- Build `dispatch/coordinator.py` — listens for detection events, manages drone state machine
- Django API receives detection → queues dispatch job → coordinator picks up
- Flight states: `DOCKED | LAUNCHING | NAVIGATING | HOVERING | DROPPING | RETURNING | LANDING | CHARGING`
- Prevent duplicate dispatches to the same target
- Add dashboard view showing: live camera feed, detection log, drone state, flight history
- Handle failure states: low battery abort, lost connection RTH

**Success criteria:** Fully automated cycle from slug detection to return-to-dock with no manual input.

**YouTube angle:** "It works... kind of. Here's everything that went wrong."

---

### Phase 6 — Charging Dock & Overnight Autonomy

**Goal:** Drone returns, docks, charges, and is ready for the next dispatch without human intervention.

**Tasks:**
- Design and 3D print dock with alignment guides — ArUco marker on dock for visual precision landing
- Implement pogo-pin charging circuit (easier to align than wireless for a custom build)
- Add battery level polling via MAVLink — only dispatch if above threshold (e.g. 60%)
- Run overnight test with logging
- Review morning logs and footage

**Success criteria:** Drone runs autonomously overnight, executes at least one real slug dispatch, returns and charges.

**YouTube angle:** "I let it run all night. Here's what happened."

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| PID tuning takes longer than expected | Budget a full weekend, film it all, it's good content |
| Wind affects outdoor hover accuracy | Optical flow + only dispatch below wind speed threshold |
| Salt dispersal inaccurate | Design hopper into frame, tune from fixed height, ±5cm is sufficient |
| Pi Zero too slow for real-time inference | Offload detection to a separate Pi 4 on the ground, Pi Zero only runs dronekit |
| Battery too low mid-flight | MAVLink battery monitoring + low-battery RTH failsafe in ArduPilot |
| Camera calibration drifts over time | Automated recalibration script on a schedule |
| Optical flow loses tracking on wet soil | Test on representative surfaces, add barometer hold as fallback |
| dronekit deprecated / unmaintained | Fallback to raw `pymavlink` — same protocol, more verbose |

---

## Milestones

| Milestone | Phase | Done |
|---|---|---|
| Stable manual flight achieved | 0 | ☐ |
| First autonomous takeoff/land via dronekit | 1 | ☐ |
| Slug detected in test conditions | 2 | ☐ |
| Pixel → real-world coordinate working | 3 | ☐ |
| GPS-free position hold confirmed | 3 | ☐ |
| Salt drop on marked target | 4 | ☐ |
| First fully automated cycle | 5 | ☐ |
| Overnight autonomous run | 6 | ☐ |

---

## Getting Started

```bash
pip install dronekit pymavlink ultralytics opencv-python django psycopg2-binary
```

Hardware first: source components, solder, flash ArduPilot, tune manually. Do not write Python until Phase 0 is complete.

First script to write (Phase 1): `drone/flight.py` — connect to FC via MAVLink, arm, takeoff, fly forward 50cm, return, land, disarm.
