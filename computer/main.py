import hashlib
import math
import os

from PIL import Image
from dotenv import load_dotenv
from pathlib import Path
import customtkinter
import paho.mqtt.client as mqtt
import requests

# MQTT
BROKER = "public.mqttserver.eu"
PORT = 1883
OUT_TOPIC = "ugent/MMM/GeoQuest/computer"
IN_TOPIC = "ugent/MMM/GeoQuest/arduino"

# Belfort van Gent als centrum
BELFORT_LAT = 51.0537
BELFORT_LON = 3.7250

AREA_SIZE_KM = 3.0
HALF_AREA_KM = AREA_SIZE_KM / 2

# Mapbox
load_dotenv()

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

BASE_DIR = Path(__file__).resolve().parent

def get_route_points(location: tuple[float, float], destination: tuple[float, float]) -> tuple[str, str, list[list[float]]]:
    location_str = f"{location[0]},{location[1]}"
    destination_str = f"{destination[0]},{destination[1]}"

    data = requests.get(
        f"https://api.mapbox.com/directions/v5/mapbox/walking/{location_str};{destination_str}",
        params={
            "access_token": MAPBOX_TOKEN,
            "geometries": "geojson"
        }
    )

    directions = data.json()

    if directions.get("code") != "Ok":
        print("Mapbox error:", directions)
        return (
            "Distance: / km",
            "Duration: / minutes",
            []
        )

    route = directions["routes"][0]

    distance_km = route["distance"] / 1000
    duration_min = route["duration"] / 60
    route_points = route["geometry"]["coordinates"]

    return (
        f"Distance: {distance_km:.2f} km",
        f"Duration: {duration_min:.0f} minutes",
        route_points
    )

def word_to_location(word: str) -> tuple[float, float]:
    """Hash the word and map it uniformly to a 3 km x 3 km square
    centered approximately on the Belfort.
    Returns (longitude, latitude).
    """
    digest = hashlib.sha256(word.encode("utf-8")).digest()

    # First half of the hash -> x coordinate
    # Second half -> y coordinate
    x_fraction = int.from_bytes(digest[:16], "big") / (2**128)
    y_fraction = int.from_bytes(digest[16:32], "big") / (2**128)

    # Convert [0, 1] to [-1.5, +1.5] km
    x_km = (x_fraction - 0.5) * AREA_SIZE_KM
    y_km = (y_fraction - 0.5) * AREA_SIZE_KM

    # Convert km offsets to latitude/longitude
    dlat = y_km / 111.32
    dlon = x_km / (111.32 * math.cos(math.radians(BELFORT_LAT)))

    lat = BELFORT_LAT + dlat
    lon = BELFORT_LON + dlon

    return lon, lat

class GeoQuest:
    def __init__(self) -> None:
        self.word: str | None = None
        self.destination: tuple[float, float] | None = None

        # MQTT
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(BROKER, PORT)
        self.client.loop_start()

        # UI
        self.app = customtkinter.CTk()
        self.app.title("GeoQuest")
        self.app.geometry("600x400")
        
        self.create_start_screen()

    def __del__(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, _userdata, _flags, _reason_code, _properties):
        print("Connected to MQTT broker!")
        client.subscribe(IN_TOPIC)

    def on_message(self, client, userdata, msg):
        message = msg.payload.decode()
        print(f"Received on {msg.topic}: {message}")

    def create_start_screen(self) -> None:
        self.title_label = customtkinter.CTkLabel(
            self.app,
            text="Welcome to GeoQuest!",
            font=("Arial", 24)
        )

        self.text_input = customtkinter.CTkEntry(
            self.app,
            placeholder_text="Enter a word",
            width=200,
            height=30,
            border_width=2,
            corner_radius=10
        )

        self.start_button = customtkinter.CTkButton(
            self.app,
            text="Start Game",
            command=self.start_game,
            width=200,
            height=30,
            border_width=2,
            corner_radius=10
        )

        self.error_label = customtkinter.CTkLabel(
            self.app,
            text="Please enter a word to start the game.",
            font=("Arial", 14),
            text_color="red"
        )

        self.image = customtkinter.CTkImage(
            light_image=Image.open(BASE_DIR / "../media/logo.png"),
            dark_image=Image.open(BASE_DIR / "../media/logo.png"),
            size=(100, 100)
        )

        self.image_label = customtkinter.CTkLabel(
            self.app,
            image=self.image,
            text=""
        )

        self.title_label.place(relx=0.5, rely=0.2, anchor="center")
        self.text_input.place(relx=0.5, rely=0.4, anchor="center")
        self.start_button.place(relx=0.5, rely=0.5, anchor="center")
        self.image_label.place(relx=0.5, rely=0.7, anchor="center")

    def start_game(self) -> None:
        word = self.text_input.get()

        if not word:
            self.error_label.place(relx=0.5, rely=0.3, anchor="center")
            return

        self.word = word
        self.destination = word_to_location(word)

        lon, lat = self.destination

        print(f"Starting game with word: {self.word}")
        print(f"Hashed location (lon, lat): {lon:.6f}, {lat:.6f}")

        dist_str, dur_str, points = get_route_points((BELFORT_LON, BELFORT_LAT), (lon, lat))
        print(points)

        self.create_game_screen(dist_str, dur_str, lon, lat)

    def create_game_screen(self, dist: str, dur: str, lon: float, lat: float) -> None:
        self.start_button.destroy()
        self.text_input.destroy()
        self.title_label.destroy()
        self.image_label.destroy()
        self.error_label.destroy()
        self.start_text = customtkinter.CTkLabel(
            self.app,
            text=(
                f"Game started!\n"
                f"Word: {self.word}\n"
                f"Destination: {lon:.6f}, {lat:.6f}\n"
                f"{dist}\n{dur}\n"
                f"Check your Arduino!"
            ),
            font=("Arial", 18)
        )

        self.start_text.place(relx=0.5, rely=0.5, anchor="center")

    def run(self) -> None:
        self.app.mainloop()


if __name__ == "__main__":
    game = GeoQuest()
    game.run()
