import hashlib
import math
from dataclasses import dataclass, field

import requests
from config import (
    AREA_SIZE_KM,
    BELFORT_LAT,
    BELFORT_LON,
    KM_PER_DEGREE_LAT,
    LOCATION_PREFIX,
    MAPBOX_DIRECTIONS_URL,
    MAPBOX_TOKEN,
    REQUEST_TIMEOUT_S,
)

Point = tuple[float, float]  # (longitude, latitude)
def point_from_list(pos: list[float]) -> Point:
    return (pos[0], pos[1])

@dataclass
class Route:
    distance_str: str = "Distance: / km"
    duration_str: str = "Duration: / minutes"
    duration: float = 0
    points: list[list[float]] = field(default_factory=list)

def word_to_location(word: str) -> Point:
    """Hash a word and map it uniformly onto a square area centred on the Belfort.

    Returns (longitude, latitude).
    """
    digest = hashlib.sha256(word.encode("utf-8")).digest()

    # First half of the hash -> x fraction, second half -> y fraction
    x_fraction = int.from_bytes(digest[:16], "big") / 2**128
    y_fraction = int.from_bytes(digest[16:], "big") / 2**128

    # Offsets in km, in [-AREA_SIZE_KM / 2, +AREA_SIZE_KM / 2]
    x_km = (x_fraction - 0.5) * AREA_SIZE_KM
    y_km = (y_fraction - 0.5) * AREA_SIZE_KM

    km_per_degree_lon = KM_PER_DEGREE_LAT * math.cos(math.radians(BELFORT_LAT))
    return (
        BELFORT_LON + x_km / km_per_degree_lon,
        BELFORT_LAT + y_km / KM_PER_DEGREE_LAT,
    )

def get_route(origin: Point, destination: Point) -> Route:
    """Ask Mapbox for a walking route. Returns an empty Route on failure."""
    coordinates = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"

    try:
        response = requests.get(
            f"{MAPBOX_DIRECTIONS_URL}/{coordinates}",
            params={"access_token": MAPBOX_TOKEN, "geometries": "geojson"},
            timeout=REQUEST_TIMEOUT_S,
        )
        directions = response.json()
    except (requests.RequestException, ValueError) as error:
        print("Error: Mapbox request failed:", error)
        return Route()

    if directions.get("code") != "Ok":
        print("Error: Mapbox", directions)
        return Route()

    route = directions["routes"][0]
    return Route(
        distance_str=f"Distance: {route['distance'] / 1000:.2f} km",
        duration_str=f"Duration: {route['duration'] / 60:.0f} minutes",
        duration=route['duration'],
        points=route["geometry"]["coordinates"] + [[destination[0], destination[1]]],
    )


def parse_location(message: str) -> Point | None:
    """Parse a 'LOC<lon>,<lat>' message. Returns None if it is not one."""
    if not message.startswith(LOCATION_PREFIX):
        print(f"WARNING: expected location, got '{message}'")
        return None

    try:
        lon, lat = message[len(LOCATION_PREFIX):].split(",")
        return float(lon), float(lat)
    except ValueError:
        print(f"WARNING: malformed location: '{message}'")
        return None

def haversine_distance(a: Point, b: Point) -> float:
    r = 6371000
    rad = math.pi / 180
    p1, p2 = a[1]*rad, b[1]*rad
    dp, dl = (b[1]-a[1])*rad, (b[0]-a[0])*rad
    h = math.sin(dp/2)*math.sin(dp/2) \
        + math.cos(p1)*math.cos(p2)*math.sin(dl/2)*math.sin(dl/2)
    return 2 * r * math.asin(math.sqrt(h))

