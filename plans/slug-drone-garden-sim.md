# Slug Drone — Garden Simulator

## Overview

A Django-based garden simulation environment that runs the full dispatch stack against a simulated drone flying over a satellite map of your actual garden. Uses ArduPilot SITL for the drone, Leaflet.js for the map, and a slug spawner that fires fake detection events at Django's API on a schedule.

Django has no idea the detections are fake. The entire coordinator, state machine, flight logic, and dashboard run exactly as they would at night with real hardware.

---

## What It Does

- Displays a satellite map of your garden with real GPS coordinates
- Plots slug detection events as markers on the map
- Shows the drone position updating in real time from SITL telemetry
- Draws the flight path as a line
- Marks the dock position
- Lets you define which garden beds are active monitoring zones
- Fires fake slug detections on a configurable schedule
- Runs at up to 10x speed so you can simulate a full night in minutes
- Logs everything to PostgreSQL exactly as the real system would

---

## Architecture

```
ArduPilot SITL
  └── Simulated drone at your garden's GPS coordinates
  └── MAVLink telemetry over TCP

Django (existing control plane)
  ├── garden_sim app (new)
  │   ├── Slug spawner — fires fake detection events
  │   ├── MAVLink telemetry consumer — reads drone position from SITL
  │   └── WebSocket — pushes drone position + detections to browser
  ├── api/ — receives detection events (unchanged)
  ├── dispatch/ — coordinator state machine (unchanged)
  └── dashboard/ — existing dashboard + new map view

Browser
  └── Leaflet.js map with satellite tiles
  └── Live drone position overlay
  └── Detection markers
  └── Bed zone overlays
```

---

## Project Structure

```
slug-drone/
├── control/
│   ├── garden_sim/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── views.py              # Map view
│   │   ├── consumers.py          # WebSocket — live drone position
│   │   ├── telemetry.py          # MAVLink position reader from SITL
│   │   ├── spawner.py            # Fake slug detection scheduler
│   │   ├── fixtures.py           # Predefined slug spawn coordinates
│   │   ├── urls.py
│   │   └── templates/
│   │       └── garden_sim/
│   │           └── map.html      # Leaflet map + WebSocket client
│   └── settings/
└── requirements.txt
```

---

## Setup

### 1 — Get Your Garden Coordinates

Open Google Maps, right-click the centre of your garden, copy the coordinates. You need:
- Home latitude and longitude (dock position)
- Bounding box of the garden (for map centering)
- Coordinates of each bed you want to monitor

### 2 — Install ArduPilot SITL

```bash
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git submodule update --init --recursive
./Tools/environment_install/install-prereqs-ubuntu.sh -y
./waf configure --board sitl
./waf copter
```

### 3 — Install Python Dependencies

```bash
pip install dronekit pymavlink channels channels-redis django psycopg2-binary
```

Channels is required for WebSocket support in Django.

### 4 — Configure Garden Coordinates

Create `garden_sim/garden_config.py`:

```python
GARDEN_HOME = {
    'lat': 51.5074,       # your dock latitude
    'lon': -0.1278,       # your dock longitude
    'alt': 0,
    'heading': 0
}

GARDEN_BOUNDS = {
    'north': 51.5076,
    'south': 51.5072,
    'east': -0.1274,
    'west': -0.1282
}

BEDS = [
    {
        'name': 'Veg bed 1',
        'bounds': [
            [51.5074, -0.1278],
            [51.5075, -0.1278],
            [51.5075, -0.1276],
            [51.5074, -0.1276],
        ]
    },
]
```

### 5 — Launch SITL

```bash
cd ardupilot
sim_vehicle.py -v ArduCopter \
  --home=51.5074,-0.1278,0,0 \
  --speedup=5 \
  --out=tcp:127.0.0.1:5760 \
  --console
```

Replace coordinates with your own. `--speedup=5` runs at 5x real time. Increase to `--speedup=10` for faster overnight simulation.

### 6 — Run Django

```bash
python manage.py runserver
```

Navigate to `/garden-sim/` to open the map.

---

## Key Components

### spawner.py

Fires fake slug detection events at Django's detection API on a configurable schedule. Reads spawn positions from `fixtures.py` or generates random positions within bed boundaries.

```python
import time
import random
import requests
from .garden_config import BEDS
from .fixtures import SLUG_POSITIONS

class SlugSpawner:
    def __init__(self, interval_min=30, interval_max=120, use_fixtures=True):
        self.interval_min = interval_min
        self.interval_max = interval_max
        self.use_fixtures = use_fixtures

    def run(self):
        while True:
            position = self._next_position()
            self._fire_detection(position)
            wait = random.randint(self.interval_min, self.interval_max)
            time.sleep(wait)

    def _next_position(self):
        if self.use_fixtures and SLUG_POSITIONS:
            return random.choice(SLUG_POSITIONS)
        return self._random_bed_position()

    def _random_bed_position(self):
        bed = random.choice(BEDS)
        bounds = bed['bounds']
        lats = [p[0] for p in bounds]
        lons = [p[1] for p in bounds]
        return {
            'lat': random.uniform(min(lats), max(lats)),
            'lon': random.uniform(min(lons), max(lons)),
            'confidence': random.uniform(0.85, 0.99),
            'source': 'sim'
        }

    def _fire_detection(self, position):
        requests.post('http://localhost:8000/api/detections/', json={
            'lat': position['lat'],
            'lon': position['lon'],
            'confidence': position['confidence'],
            'source': position.get('source', 'sim')
        })
```

### fixtures.py

Hardcoded slug positions for repeatable testing of specific scenarios.

```python
SLUG_POSITIONS = [
    {'lat': 51.50742, 'lon': -0.12778, 'confidence': 0.94, 'source': 'sim'},
    {'lat': 51.50748, 'lon': -0.12771, 'confidence': 0.91, 'source': 'sim'},
    {'lat': 51.50739, 'lon': -0.12765, 'confidence': 0.88, 'source': 'sim'},
]
```

Use fixtures for regression testing specific dispatch scenarios. Use random spawning for general overnight simulation.

### telemetry.py

Reads drone position from SITL via MAVLink and pushes to the WebSocket channel.

```python
from dronekit import connect
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def stream_telemetry():
    vehicle = connect('tcp:127.0.0.1:5760', wait_ready=True)
    channel_layer = get_channel_layer()

    while True:
        loc = vehicle.location.global_relative_frame
        async_to_sync(channel_layer.group_send)(
            'garden_sim',
            {
                'type': 'drone_position',
                'lat': loc.lat,
                'lon': loc.lon,
                'alt': loc.alt,
                'heading': vehicle.heading,
                'battery': vehicle.battery.level,
                'state': vehicle.system_status.state
            }
        )
        time.sleep(0.5)
```

### map.html

Leaflet map with satellite tiles, WebSocket client for live drone position, and detection marker rendering.

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
  <style>
    #map { height: 100vh; width: 100%; }
    #status { position: absolute; top: 10px; right: 10px; z-index: 1000;
              background: white; padding: 10px; border-radius: 4px; }
  </style>
</head>
<body>
<div id="map"></div>
<div id="status">
  <div>State: <span id="drone-state">—</span></div>
  <div>Battery: <span id="drone-battery">—</span></div>
  <div>Altitude: <span id="drone-alt">—</span></div>
</div>

<script>
  const HOME = { lat: {{ home_lat }}, lon: {{ home_lon }} };

  const map = L.map('map').setView([HOME.lat, HOME.lon], 20);

  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri',
    maxZoom: 22
  }).addTo(map);

  // Dock marker
  L.marker([HOME.lat, HOME.lon], {
    icon: L.divIcon({ className: '', html: '🏠', iconSize: [20, 20] })
  }).addTo(map).bindPopup('Dock');

  // Bed overlays
  {% for bed in beds %}
  L.polygon({{ bed.bounds|safe }}, {
    color: '#00ff00', fillOpacity: 0.1, weight: 1
  }).addTo(map).bindPopup('{{ bed.name }}');
  {% endfor %}

  // Drone marker
  const droneIcon = L.divIcon({ className: '', html: '🚁', iconSize: [20, 20] });
  const drone = L.marker([HOME.lat, HOME.lon], { icon: droneIcon }).addTo(map);
  const flightPath = L.polyline([], { color: '#0088ff', weight: 2 }).addTo(map);
  const pathPoints = [];

  // Detection markers
  function addDetection(lat, lon, confidence) {
    L.circleMarker([lat, lon], {
      radius: 6, color: '#ff4444', fillOpacity: 0.8
    }).addTo(map).bindPopup(`Slug detected (${(confidence * 100).toFixed(0)}%)`);
  }

  // WebSocket
  const ws = new WebSocket('ws://' + window.location.host + '/ws/garden-sim/');

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'drone_position') {
      const pos = [data.lat, data.lon];
      drone.setLatLng(pos);
      pathPoints.push(pos);
      flightPath.setLatLngs(pathPoints);
      document.getElementById('drone-state').textContent = data.state;
      document.getElementById('drone-battery').textContent = data.battery + '%';
      document.getElementById('drone-alt').textContent = data.alt.toFixed(1) + 'm';
    }

    if (data.type === 'detection') {
      addDetection(data.lat, data.lon, data.confidence);
    }
  };
</script>
</body>
</html>
```

---

## Simulation Scenarios

Define these as management commands or fixtures to run repeatable tests.

| Scenario | What It Tests |
|---|---|
| Single detection, drone at dock | Basic dispatch cycle |
| Detection fires while drone in flight | Duplicate dispatch prevention |
| Two detections in quick succession | Queue handling |
| Detection fires with battery at 30% | Low battery abort |
| Detection in far corner of garden | Max range navigation |
| Multiple detections across all beds | Full overnight simulation |
| SITL connection drops mid-flight | Lost connection RTH |

Run overnight scenario:
```bash
python manage.py run_scenario --scenario=overnight --speedup=10
```

---

## Django Management Commands

```
python manage.py start_spawner          # start random slug spawner
python manage.py start_spawner --fixtures  # use fixture positions only
python manage.py start_telemetry        # start SITL telemetry stream
python manage.py run_scenario --scenario=overnight --speedup=10
python manage.py clear_sim_data         # wipe detection + flight logs
```

---

## Milestones

| Milestone | Done |
|---|---|
| SITL launches at garden coordinates | ☐ |
| Drone visible on Leaflet satellite map | ☐ |
| Fake detection fires and appears on map | ☐ |
| Full dispatch cycle completes in sim | ☐ |
| Drone position tracks in real time on map | ☐ |
| Low battery abort scenario passes | ☐ |
| Overnight scenario runs at 10x speed | ☐ |
| All scenario tests passing | ☐ |

---

## Getting Started

```bash
pip install dronekit pymavlink channels channels-redis
```

1. Add your garden coordinates to `garden_config.py`
2. Launch SITL with your home coordinates
3. Run Django with Channels (requires Redis for WebSocket layer)
4. Open `/garden-sim/` in browser
5. Run `python manage.py start_spawner` to begin firing detections
