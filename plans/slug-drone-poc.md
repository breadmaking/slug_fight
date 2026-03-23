# Slug Drone — Proof of Concept Plan

## Overview

Before spending £250+ on drone hardware, prove every major subsystem works in software first. The POC costs ~£10 and validates the full stack. Hardware is only introduced once the software is solid.

---

## Core Principle

The three things that need proving are independent of each other. Prove them separately, then integrate.

| Subsystem | Proves | Hardware Needed |
|---|---|---|
| Detection | YOLOv8n can identify slugs reliably | Laptop + webcam |
| Flight logic | Python can control a drone autonomously | ArduPilot SITL (simulated) |
| Payload | Salt can be dispensed reliably on trigger | Arduino Nano + servo |

**Total hardware cost: ~£10**

---

## Bill of Materials

| Item | Source | Cost |
|---|---|---|
| Arduino Nano (clone) | AliExpress | ~£4 |
| Micro servo (SG90 or similar) | AliExpress / Amazon | ~£3 |
| Jumper wires | AliExpress / Amazon | ~£2 |
| Webcam (if you don't have one) | Amazon | £0-20 |
| **Total** | | **~£7-10** |

Everything else runs on your laptop.

---

## POC Phases

### POC Phase 1 — Slug Detection

**Goal:** YOLOv8n detects slugs from a camera feed with >85% accuracy and outputs a pixel-space bounding box.

**Setup:**
- Laptop + any webcam or phone camera
- A slug (or slug images) in a tray or on soil

**Tasks:**
- Install `ultralytics` and run YOLOv8n inference on a webcam feed
- Source a slug dataset from Roboflow or collect your own images
- Fine-tune YOLOv8n on slug images
- Output: class, confidence score, bounding box centre pixel coordinates
- Log detections to a local PostgreSQL database via Django

**Success criteria:** Detects a slug in varied lighting conditions with >85% confidence. Runs at 5+ fps on laptop CPU.

**Stack:**
```bash
pip install ultralytics opencv-python django psycopg2-binary
```

---

### POC Phase 2 — Flight Logic (SITL)

**Goal:** Full autonomous flight sequence runs in Python against a simulated drone, including takeoff, navigation to a coordinate, payload trigger signal, and return to home.

**Setup:**
- ArduPilot SITL installed on laptop
- dronekit connecting to the simulated drone via TCP

**Tasks:**
- Install ArduPilot SITL and verify simulated drone connects
- Write `drone/flight.py` — arm, takeoff, fly to XY offset, return, land, disarm
- Write `dispatch/coordinator.py` — state machine that receives a detection event and runs the flight sequence
- Hook coordinator to Django API — detection fires → Django queues dispatch → coordinator executes
- Simulate a detection event manually and watch the full cycle run in SITL
- Add battery level monitoring (SITL exposes this)
- Test failure states: low battery abort, mid-flight cancel

**Installing SITL:**
```bash
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git submodule update --init --recursive
./Tools/environment_install/install-prereqs-ubuntu.sh -y
./waf configure --board sitl
./waf copter
sim_vehicle.py -v ArduCopter --console --map
```

**Connecting dronekit:**
```bash
pip install dronekit pymavlink
```

```python
from dronekit import connect
vehicle = connect('tcp:127.0.0.1:5760', wait_ready=True)
```

**Success criteria:** Full dispatch cycle runs end-to-end in simulation — detection event fires → coordinator picks up → SITL drone arms, takes off, navigates to coordinate, returns, lands → state returns to DOCKED.

---

### POC Phase 3 — Payload Mechanism

**Goal:** A servo-triggered salt gate reliably dispenses a measured dose on command from Python over serial.

**Setup:**
- Arduino Nano wired to SG90 servo
- Servo arm attached to a simple card or 3D printed gate over a salt container
- Python script on laptop sending serial commands to the Nano

**Wiring:**
```
Arduino Nano pin 9 → Servo signal wire (orange)
Arduino Nano 5V   → Servo power (red)
Arduino Nano GND  → Servo ground (brown)
```

**Arduino sketch:**
```cpp
#include <Servo.h>
Servo gate;

void setup() {
  Serial.begin(9600);
  gate.attach(9);
  gate.write(0);
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'O') {
      gate.write(90);
      delay(500);
      gate.write(0);
    }
  }
}
```

**Python trigger:**
```python
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 9600)
time.sleep(2)
ser.write(b'O')
ser.close()
```

**Tasks:**
- Build the bench rig — Arduino, servo, makeshift gate, salt container
- Tune gate open duration for correct salt dose
- Test dispersal pattern from 30cm height into a tray
- Integrate serial trigger into `drone/payload.py`
- Hook payload trigger into the SITL dispatch cycle at the hover waypoint

**Success criteria:** Salt drops within a 5cm radius of target consistently. Trigger fires reliably from Python over serial.

---

### POC Phase 4 — Integration

**Goal:** All three subsystems run together end-to-end on the laptop.

**Tasks:**
- Detection fires → Django → coordinator → SITL flight cycle → payload trigger at waypoint → return
- Django dashboard shows: live camera feed, detection log, simulated drone state, flight history
- Run 10 consecutive full cycles with no manual intervention

**Success criteria:** Full automated cycle runs reliably in simulation with real payload hardware triggering correctly.

---

## Project Structure (POC)

```
slug-drone/
├── control/                  # Django project
│   ├── api/                  # Detection intake + dispatch queue
│   ├── dashboard/            # Live monitoring UI
│   └── settings/
├── detection/
│   ├── model/                # YOLOv8 weights
│   └── stream.py             # Webcam feed + inference loop
├── drone/
│   ├── flight.py             # dronekit flight logic (SITL or real)
│   ├── payload.py            # Serial trigger to Arduino
│   └── dock.py               # Dock state management
├── dispatch/
│   └── coordinator.py        # State machine
├── hardware/
│   └── payload_gate/         # Arduino sketch + wiring diagram
└── requirements.txt
```

---

## Milestones

| Milestone | Phase | Done |
|---|---|---|
| Slug detected on webcam | 1 | ☐ |
| Detection logged to Django | 1 | ☐ |
| SITL drone arms and takes off via dronekit | 2 | ☐ |
| Full simulated flight cycle completes | 2 | ☐ |
| Salt gate triggers from Python | 3 | ☐ |
| Dispersal pattern acceptable | 3 | ☐ |
| Full end-to-end cycle in simulation | 4 | ☐ |

---

## When to Move to Real Hardware

Move to the full hardware build when:
- All POC milestones are checked off
- The Django dashboard is showing clean cycle logs
- You are confident in the state machine and failure handling
- The payload mechanism is tuned

At that point you are swapping:
- SITL → real ArduPilot FC
- Laptop webcam → Pi 4 + IR camera on a pole
- `tcp:127.0.0.1:5760` → UART serial to FC from Pi Zero 2W
- Bench servo → onboard hopper servo

The Python code changes minimally. The dronekit connection string and the serial port are the main differences.

---

## Getting Started

```bash
pip install dronekit pymavlink ultralytics opencv-python django psycopg2-binary pyserial
```

Start with POC Phase 1 — get a slug detected on your webcam. Everything else follows from there.
