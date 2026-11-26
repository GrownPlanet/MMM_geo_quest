from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
# Use the mapbox api
# MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/walking"
# Or our own server
MAPBOX_DIRECTIONS_URL = "http://localhost:8080/"
REQUEST_TIMEOUT_S = 10

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "../media/logo.png"

# MQTT
BROKER = "public.mqttserver.eu"
PORT = 1883
OUT_TOPIC = "ugent/MMM/GeoQuest/computer"
IN_TOPIC = "ugent/MMM/GeoQuest/arduino"

LOCATION_PREFIX = "LOC"
POLL_INTERVAL_MS = 100

# The Belfort of Ghent is the centre of the play area
BELFORT_LON = 3.7250
BELFORT_LAT = 51.0537
AREA_SIZE_KM = 3.0
KM_PER_DEGREE_LAT = 111.32

MIN_DIST_M = 15
