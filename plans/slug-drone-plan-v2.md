# Slug Drone Project — Full Build Plan v2

## Overview

An automated garden defence system using a custom-built drone to detect and neutralise slugs with a single-shot salt payload. Built iteratively for YouTube documentation. The drone carries minimal compute — all intelligence runs on a ground station. The dock handles reloading and charging alignment via a guide rail system.

---

## Architecture

```
Ground Station (laptop or Pi 4)
├── Django control plane + dashboard
├── YOLOv8 inference server (ground camera + drone camera feed)
├── Dispatch coordinator (state machine)
└── PostgreSQL (detections, flight logs, footage)

Drone
├── Pi Zero W
│   ├── Downward camera → UDP stream to ground server
│   └── Receives {x_error, y_error, confidence} from server
├── Teensy 4.0
│   ├── Proportional controller at 100Hz
│   ├── MAVLink to FC
│   └── Salt gate servo trigger
└── Matek H743 FC
    └── ArduPilot (stabilisation, motors, RTH failsafe)

Dock
├── Guide rail / funnel (passive mechanical alignment)
├── Gravity hopper + dock servo (one-shot salt reload)
└── Pogo-pin charging contacts
```

---

## How It Works End to End

1. Ground camera overlooks the bed, YOLOv8 detects a slug
2. Approximate real-world coordinates calculated via homography
3. Django queues a dispatch job
4. Coordinator arms the drone, sends it to approximate coordinates
5. Drone camera streams to ground server, server runs inference
6. Server returns `{x_error, y_error, confidence}` to Pi Zero over UDP
7. Pi Zero forwards offset to Teensy
8. Teensy runs proportional controller, nudges drone until slug is centred
9. When confidence high and error within threshold, Teensy triggers salt gate
10. All salt in chamber drops on slug
11. Drone returns to dock, slides into guide rails, lands in precise position
12. Dock servo releases one measured shot of salt into drone chamber
13. Pogo pins connect, battery begins charging
14. Ready for next dispatch

---

## Bill of Materials

| Component | Example Part | Approx Cost |
|---|---|---|
| Flight controller | Matek H743 Slim V4 | £50-70 |
| Frame | 5" racing frame (TBS Source One) | £15-25 |
| Motors x4 | SpeedyBee 2306.5 1800KV | £30-50 |
| 4-in-1 ESC | SpeedyBee BLS 55A | £25-40 |
| LiPo battery | 4S 1300-1800mAh | £20-35 |
| LiPo charger | ISDT 405AC | £20-30 |
| Radio TX | Radiomaster Pocket ELRS | £75 |
| Radio RX | SpeedyBee Nano ELRS (PA/LNA) | £12-15 |
| Companion computer | Raspberry Pi Zero W | £10-15 |
| Drone camera | Pi Camera Module 3 | £25 |
| Real-time controller | Teensy 4.0 | £20 |
| Salt gate servo | SG90 micro servo | £3-5 |
| Ground camera | Pi Camera / IR webcam | £20-35 |
| Ground station | Pi 4 or existing laptop | £0-60 |
| Props, wiring, connectors | Various | £10-15 |
| **Total** | | **~£335-490** |

---

## UK Suppliers

| Component | Supplier | Link |
|---|---|---|
| Matek H743 V4 | 3DXR | https://www.3dxr.co.uk |
| Matek H743 V4 | Unmanned Tech | https://www.unmannedtechshop.co.uk |
| SpeedyBee ESC | HobbyRC | https://www.hobbyrc.co.uk |
| 5" Frames | HobbyRC | https://www.hobbyrc.co.uk/5-inch-quad-frames-2 |
| SpeedyBee motors | Flying Tech | https://www.flyingtech.co.uk |
| Radiomaster Pocket | Amazon UK | https://www.amazon.co.uk |
| ELRS Nano RX | Flying Tech | https://www.flyingtech.co.uk |
| ISDT 405AC charger | Flying Tech | https://www.flyingtech.co.uk |
| Pi Zero W | The Pi Hut | https://thepihut.com |
| Pi Camera Module 3 | The Pi Hut | https://thepihut.com |

---

## Tech Stack

- Python — drone control, detection, dispatch logic
- Django — control plane, monitoring UI, API layer
- ArduPilot — FC firmware (stabilisation, motor control, failsafes)
- `dronekit` / `pymavlink` — Python MAVLink interface
- YOLOv8 (`ultralytics`) — slug detection (ground + drone camera)
- OpenCV — camera feeds, homography calibration, UDP streaming
- Teensy 4.0 (Arduino/C++) — real-time proportional controller, servo trigger
- PostgreSQL — detections, flight events, logs
- Mission Planner / QGroundControl — FC configuration (one-time setup)

---

## Project Structure

```
slug-drone/
├── control/                  # Django project
│   ├── api/                  # Detection intake, dispatch queue
│   ├── dashboard/            # Live monitoring UI
│   └── settings/
├── detection/
│   ├── model/                # YOLOv8 weights (ground + drone)
│   ├── calibration/          # Homography camera-to-world mapping
│   ├── ground_stream.py      # Ground camera inference loop
│   └── drone_stream.py       # UDP receiver + drone camera inference
├── drone/
│   ├── flight.py             # dronekit flight logic
│   ├── payload.py            # Serial trigger to Teensy
│   └── dock.py               # Dock state + reload handshake
├── dispatch/
│   └── coordinator.py        # State machine
├── teensy/
│   └── controller.ino        # Proportional controller + MAVLink + servo
├── hardware/
│   ├── frame/                # CAD files
│   ├── hopper/               # Salt chamber + gate STLs
│   └── dock/                 # Guide rail + reload mechanism STLs
├── scripts/
└── requirements.txt
```

---

## Payload Design

### One-Shot Architecture
The drone carries a single fixed chamber loaded with one dose of salt (~2-3g). All salt drops on trigger. No dosing mechanism needed on the drone — just a gate servo that opens fully and closes.

### Salt Chamber
- Small 3D printed box integrated into the frame, not bolted on
- Designed with a funnel inlet at the top for dock reloading
- SG90 servo gate on the bottom
- Desiccant pad inside to prevent clumping (gardens are damp at night)

### Dock Reload Mechanism
- Gravity hopper mounted on dock above the landing position
- Single dock-side servo releases one measured shot when drone is docked
- Shot drops through a tube that aligns with the drone chamber funnel
- Reload is triggered automatically once landing is confirmed

### Why One Shot
- Simpler drone hardware — one servo, one chamber, no dosing logic
- No mid-flight clumping risk — chamber is reloaded fresh each dispatch
- Consistent dose — dock-side dispenser is calibrated once and stays consistent
- Less weight on drone — 2-3g of salt is negligible

---

## Dock Design

### Guide Rail System
Drone does not need to land precisely — it needs to land within the entry zone (~10-15cm). The physical geometry does the rest.

```
Wide funnel entry (~15cm opening)
        ↓ tapered guide rails
Precise dock position (±1-2cm)
        ↓
Salt refill tube aligns with chamber funnel
Pogo pins align with battery contacts
```

### Design Principles
- Smooth taper — guides on the way down, does not trap on takeoff
- Drone lifts straight up to clear rails cleanly
- Prototype in cardboard before printing
- ArUco marker on dock for visual landing assist — gets drone into the entry zone, rails handle the rest

### Charging
- Pogo-pin contacts at fixed dock position
- Manual charge initiation for v1 (ISDT requires confirmation)
- Pi Zero monitors battery via MAVLink, reports to Django when charging needed
- Fully automated charging is a v2 goal requiring a smart BMS

---

## Camera System

### Ground Camera
- Wide angle, fixed position overlooking the full bed
- Runs 24/7, streams to Django inference server
- Detects slug, calculates approximate real-world XY via homography
- ArUco markers in the bed used for calibration grid
- IR illumination for night operation

### Drone Camera
- Pi Camera Module 3, downward facing
- Streams 320x320 JPEG frames at 15fps over UDP to ground server
- Ground server runs YOLOv8 inference, returns `{x_error, y_error, confidence}`
- Used for visual servo homing once drone reaches approximate coordinates
- Same model weights as ground camera, possibly fine-tuned on downward-facing slug images

### Why Server-Side Inference
- Pi Zero W cannot run YOLOv8 at useful frame rates while managing comms
- Ground station has headroom to run YOLOv8s or YOLOv8m (better accuracy)
- Model retraining and redeployment requires no changes to drone hardware
- Django integration is natural — inference runs in the same process as control plane
- Use UDP for streaming — dropped frames are better than late frames in a control loop

---

## Teensy 4.0 Role

The Teensy handles everything that requires deterministic real-time timing, which Linux on the Pi Zero cannot guarantee.

**Responsibilities:**
- Receives `{x_error, y_error}` offset from Pi Zero over UART
- Runs proportional controller at fixed 100Hz
- Generates MAVLink SET_POSITION_TARGET messages to FC
- Triggers salt gate servo with microsecond precision
- Confirms gate closed after drop

**Why Not Just dronekit:**
- Linux OS scheduler introduces jitter in control loops
- Visual servo corrections need to fire at consistent intervals
- Oscillation in the correction loop causes the drone to wobble over the target

**When to Add It:**
Not required for POC or SITL testing. Add when moving to real hardware if visual servo loop shows oscillation.

---

## Phases

### Phase 0 — Build & Tune

**Goal:** Stable manual flight before a line of Python is written.

**Tasks:**
- Source and solder all components
- Flash ArduPilot to FC via Mission Planner
- Configure ExpressLRS radio
- PID tune — expect a weekend of crashes
- Set RTH failsafe on signal loss
- Verify failsafe works before any autonomous testing

**Success criteria:** Stable 2+ minute hover, clean landing, RTH confirmed.

**YouTube angle:** "Building a slug drone from scratch — day one. Here's everything that broke."

---

### Phase 1 — Python Flight Control

**Goal:** dronekit controls the drone autonomously via MAVLink.

**Tasks:**
- Connect Pi Zero to FC via UART
- Arm → takeoff → fly to XY offset → return → land → disarm
- Battery monitoring and low-battery abort
- 10 consecutive clean cycles

**Notes:**
- Radio TX on hand throughout for manual override
- Use guided mode with relative position offsets, not GPS waypoints

**Success criteria:** 10 clean autonomous cycles with no manual intervention.

---

### Phase 2 — Slug Detection (Ground Camera)

**Goal:** Ground camera detects slugs reliably and logs to Django.

**Tasks:**
- Mount camera + IR illumination over test bed
- Fine-tune YOLOv8n on slug dataset (Roboflow)
- Output bounding box + confidence to Django via API
- Log all detections to PostgreSQL

**Success criteria:** >85% accuracy in outdoor night conditions.

**YouTube angle:** "Teaching a computer to spot slugs at 2am."

---

### Phase 3 — Coordinate Translation & Positioning

**Goal:** Camera pixel coordinates translate to drone waypoints. Drone holds position without GPS.

**Tasks:**
- ArUco marker calibration grid in bed
- OpenCV homography (pixels → real-world cm)
- Django endpoint: detection event → drone waypoint
- Add optical flow sensor to FC for GPS-free hover
- Test position hold accuracy

**Success criteria:** ±3cm coordinate accuracy. Stable GPS-free hover.

---

### Phase 4 — Drone Camera & Visual Servo

**Goal:** Drone homes in on slug using its own camera once at approximate coordinates.

**Tasks:**
- Mount Pi Camera Module 3 downward on drone
- UDP stream 320x320 frames to ground inference server
- Ground server runs YOLOv8 inference, returns offset to Pi Zero
- Pi Zero forwards to Teensy (or dronekit directly for POC)
- Proportional controller nudges drone until slug centred
- Fine-tune on downward-facing slug images if needed

**Success criteria:** Drone centres on slug within 5cm from 30cm altitude.

---

### Phase 5 — Payload Mechanism

**Goal:** Single-shot salt chamber drops on command, reloads at dock.

**Tasks:**
- Design and print salt chamber integrated into frame
- SG90 servo gate, wired to Teensy
- Bench test dispersal from 30cm — tune gate open duration
- Design and print dock-side gravity hopper + reload tube
- Test reload cycle — land → dock servo → chamber fills → ready
- Re-tune PIDs with payload weight

**Success criteria:** Salt hits within 5cm of target. Reload completes reliably after landing.

---

### Phase 6 — Dock & Guide Rails

**Goal:** Drone lands in guide rail system, aligns precisely, reloads, charges.

**Tasks:**
- Prototype dock geometry in cardboard first
- Design tapered guide rails — wide entry, precise dock position
- Print final dock with salt reload tube and pogo-pin contacts
- ArUco marker on dock for visual landing assist
- Tune landing approach so drone enters entry zone reliably
- Test full land → reload → ready cycle

**Success criteria:** Consistent precise dock alignment from ArUco-guided approach + rails.

---

### Phase 7 — Integration & Dispatch Loop

**Goal:** Full automated cycle end-to-end.

**Tasks:**
- Coordinator state machine ties all phases together
- Flight states: `DOCKED | LAUNCHING | NAVIGATING | HOMING | DROPPING | RETURNING | LANDING | RELOADING | CHARGING`
- Duplicate dispatch prevention
- Django dashboard: live feeds, detection log, drone state, flight history
- Failure handling: low battery abort, lost WiFi, lost visual lock

**Success criteria:** Full automated cycle with no manual input.

**YouTube angle:** "It works... kind of. Here's everything that went wrong."

---

### Phase 8 — Overnight Autonomy

**Goal:** Runs all night, dispatches on every detection, logs everything.

**Tasks:**
- End-to-end overnight test
- Review morning logs and footage
- Tune based on real-world failure modes

**Success criteria:** At least one real slug neutralised autonomously overnight.

**YouTube angle:** "I let it run all night. Here's what happened."

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| PID tuning takes longer than expected | Budget a full weekend, film it all |
| Wind affects hover accuracy | Optical flow + wind speed threshold before dispatch |
| UDP latency causes visual servo oscillation | Reduce frame resolution, use local WiFi only, add Teensy |
| Salt clumps in chamber | Desiccant pad in chamber, reload fresh each dispatch |
| Dock reload misaligns | Funnel inlet on chamber, generous tolerances, prototype in cardboard |
| Pi Zero too slow for comms + streaming | Offload all inference server-side, Pi Zero only streams and receives offsets |
| dronekit deprecated | Fallback to raw `pymavlink` |
| Optical flow loses tracking on wet soil | Barometer hold as fallback |
| Guide rails trap drone on takeoff | Smooth taper geometry, no lip at dock position |

---

## Milestones

| Milestone | Phase | Done |
|---|---|---|
| Stable manual flight | 0 | ☐ |
| First autonomous takeoff/land | 1 | ☐ |
| Slug detected by ground camera | 2 | ☐ |
| Coordinate translation working | 3 | ☐ |
| GPS-free position hold | 3 | ☐ |
| Drone camera visual servo working | 4 | ☐ |
| Salt drop on target | 5 | ☐ |
| Dock reload cycle confirmed | 5 | ☐ |
| Guide rail alignment working | 6 | ☐ |
| First fully automated cycle | 7 | ☐ |
| Overnight autonomous run | 8 | ☐ |

---

## Getting Started

```bash
pip install dronekit pymavlink ultralytics opencv-python django psycopg2-binary pyserial
```

Hardware first. Flash ArduPilot, tune manually, confirm RTH failsafe. Do not write Python until Phase 0 is complete.

First code to write (Phase 1): `drone/flight.py` — connect to FC via MAVLink, arm, takeoff, fly forward 50cm, return, land, disarm.
