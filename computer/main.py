import hashlib
import math
import os
import queue
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path

import customtkinter
import paho.mqtt.client as mqtt
import requests
from dotenv import load_dotenv
from PIL import Image

# --- Configuration ----------------------------------------------------------

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

Point = tuple[float, float]  # (longitude, latitude)
def point_from_list(pos: list[float]) -> Point:
    return (pos[0], pos[1])

# --- Geo helpers ------------------------------------------------------------

@dataclass
class Route:
    distance: str = "Distance: / km"
    duration: str = "Duration: / minutes"
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
        distance=f"Distance: {route['distance'] / 1000:.2f} km",
        duration=f"Duration: {route['duration'] / 60:.0f} minutes",
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

# --- Application ------------------------------------------------------------

class GeoQuest:
    def __init__(self):
        self.word: str | None = None
        self.destination: Point = (0, 0)
        self.difficulty: str = "Easy"

        self.route: Route = Route(distance=f"/", duration=f"/", points=[])
        self.current_dest: Point = (0, 0)

        self.messages: queue.Queue[str] = queue.Queue()

        self._setup_mqtt()
        self._setup_window()
        self.create_start_screen()

    def _setup_mqtt(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(BROKER, PORT)
        self.client.loop_start()

    def _setup_window(self):
        self.app = customtkinter.CTk()
        self.app.title("GeoQuest")
        self.app.geometry("600x400")
        self.app.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.app.destroy()

    def on_connect(self, client, _userdata, _flags, _reason_code, _properties):
        print("Info: Connected to MQTT broker!")
        client.subscribe(IN_TOPIC)

    def on_message(self, _client, _userdata, msg):
        message = msg.payload.decode()
        self.messages.put(message)
        print(f"Info: Received on {msg.topic}: {message}")

    def create_start_screen(self):
        self.user_manual_pictogram = customtkinter.CTkImage(
            light_image=Image.open(BASE_DIR / "../media/user_manual_black.png"),
            dark_image=Image.open(BASE_DIR / "../media/user_manual_white.png"),
            size=(50, 50)
        )
        self.user_manual_button = customtkinter.CTkButton(
            self.app,
            image=self.user_manual_pictogram,
            text="",
            command=self.open_user_manual,
            width=50,
            height=50,
            border_width=1,
            fg_color="transparent",
        )

        self.title_label = customtkinter.CTkLabel(
            self.app, text="Welcome to GeoQuest!", font=("Arial", 24)
        )
        self.text_input = customtkinter.CTkEntry(
            self.app,
            placeholder_text="Enter a word",
            width=200,
            height=30,
            border_width=2,
            corner_radius=10,
        )
        self.start_button = customtkinter.CTkButton(
            self.app,
            text="Start Game",
            command=self.start_game,
            width=200,
            height=30,
            border_width=2,
            corner_radius=10,
        )
        self.difficulty_menu = customtkinter.CTkOptionMenu(
            self.app,
            values=["Easy", "Medium", "Hard", "Expert"],
            width=200,
            height=30,
            corner_radius=10
        )
        self.error_label = customtkinter.CTkLabel(
            self.app,
            text="Please enter a word to start the game.",
            font=("Arial", 14),
            text_color="red",
        )

        logo = Image.open(LOGO_PATH)
        self.image = customtkinter.CTkImage(light_image=logo, dark_image=logo, size=(100, 100))
        self.image_label = customtkinter.CTkLabel(self.app, image=self.image, text="")

        self.user_manual_button.place(relx=0.9, rely=0.9, anchor="center")
        self.title_label.place(relx=0.5, rely=0.2, anchor="center")
        self.text_input.place(relx=0.5, rely=0.4, anchor="center")
        self.difficulty_menu.place(relx=0.5, rely=0.5, anchor="center")
        self.start_button.place(relx=0.5, rely=0.6, anchor="center")
        self.image_label.place(relx=0.5, rely=0.8, anchor="center")
    
    def open_user_manual(self):
        manual_path = (BASE_DIR / "../user_manual.md").resolve()
        if manual_path.exists():
            webbrowser.open(manual_path.as_uri())
        else:
            print("Error: User manual not found.")

    def start_game(self):
        word = self.text_input.get()
        self.difficulty = self.difficulty_menu.get()

        if not word:
            self.error_label.place(relx=0.5, rely=0.3, anchor="center")
            return

        self.word = word
        self.destination = word_to_location(word)
        lon, lat = self.destination

        print(f"Info: Starting game with word: {word}")
        print(f"Info: Hashed location (lon, lat): {lon}, {lat}")
        print(f"Info: Difficulty level: {self.difficulty}")

        self.create_location_screen()

    def create_location_screen(self):
        for widget in (
            self.start_button,
            self.text_input,
            self.title_label,
            self.image_label,
            self.difficulty_menu,
            self.error_label,
        ):
            widget.destroy()

        self.wait_text = customtkinter.CTkLabel(
            self.app,
            text="Waiting on current location from arduino...",
            font=("Arial", 18),
        )
        self.wait_text.place(relx=0.5, rely=0.5, anchor="center")

        self.wait_for_initial_location()

    def calculate_points_with_difficulty(self, points: list[list[float]]) -> list[list[float]]:
        if self.difficulty == "Easy":
            return points
        elif self.difficulty == "Medium":
            # make sure the last point is included
            return points[:-1:2] + [points[-1]]
        elif self.difficulty == "Hard":
            return points[:-1:4] + [points[-1]]
        elif self.difficulty == "Expert":
            return [points[-1]]
        else:
            print("Warning: unrecognized difficulty level, defaulting to Easy")
            return points

    def set_next_location(self):
        self.current_dest = point_from_list(self.route.points.pop(0))
        self.client.publish(
            OUT_TOPIC,
            f"NEXT{self.current_dest[0]},{self.current_dest[1]}"
        )
        print(f"Info: next location: {self.current_dest}")

    def get_location(self) -> Point | None:
        current_location = None

        try:
            message = self.messages.get_nowait()
        except queue.Empty:
            return None

        return parse_location(message)

    def wait_for_initial_location(self):
        initial_location = self.get_location()
        if initial_location == None:
            self.app.after(100, self.wait_for_initial_location)
            return

        print(f"Info: initial location: {initial_location}")

        self.route = get_route(initial_location, self.destination)
        # print("Debug: points on path", route.points)
        self.route.points = self.calculate_points_with_difficulty(self.route.points)
        # print("Debug: points on reduced path", route.points)

        self.create_game_screen()

    def create_game_screen(self):
        self.wait_text.destroy()

        lon, lat = self.destination
        self.start_text = customtkinter.CTkLabel(
            self.app,
            text=(
                "Game started!\n"
                "Check your arduino.\n"
                f"Word: {self.word}\n"
            ),
            font=("Arial", 18),
        )
        self.start_text.place(relx=0.5, rely=0.5, anchor="center")

        self.set_next_location()

        self.main_game_loop()

    def main_game_loop(self):
        current_location = self.get_location()
        if current_location == None:
            self.app.after(100, self.main_game_loop)
            return

        dist = haversine_distance(current_location, self.current_dest)
        print(f"Info: new location: {current_location}; dist: {dist}")

        if dist < MIN_DIST_M:
            if len(self.route.points) == 0:
                self.arrived()
                return

            self.set_next_location()

        self.app.after(100, self.main_game_loop)

    def arrived(self):
        self.client.publish(OUT_TOPIC, "LAST")

        self.start_text.destroy()

        self.finished = customtkinter.CTkLabel(
            self.app,
            text="You did it! 🎉🎉",
            font=("Arial", 18),
        )
        self.finished.place(relx=0.5, rely=0.5, anchor="center")

    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    GeoQuest().run()
