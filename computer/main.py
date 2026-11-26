import time
import math
import webbrowser
from pathlib import Path

import customtkinter
from config import BASE_DIR, LOGO_PATH, MIN_DIST_M, POLL_INTERVAL_MS
from game import calculate_points_with_difficulty
from geo import (
    Point,
    Route,
    get_route,
    haversine_distance,
    point_from_list,
    word_to_location,
)
from mqtt import MqttClient
from PIL import Image
from route_map import create_location_map
from route_map import open_location_map as open_route_map


class GeoQuest:
    def __init__(self):
        self.word: str | None = None
        self.destination: Point = (0, 0)
        self.difficulty: str = "Easy"

        self.route: Route = Route(distance_str="/", duration_str="/", points=[])
        self.current_dest: Point = (0, 0)
        self.location_nodes: list[Point] = []
        self.last_location_recorded_at = 0.0
        self.game_start_time = 0
        self.location_map_path: Path | None = None

        self.mqtt = MqttClient()
        self._setup_window()
        self.create_start_screen()

    def _setup_window(self):
        self.app = customtkinter.CTk()
        self.app.title("GeoQuest")
        self.app.geometry("600x400")
        self.app.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        self.mqtt.close()
        self.app.destroy()

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

    def set_next_location(self):
        self.current_dest = point_from_list(self.route.points.pop(0))
        self.mqtt.send_next_location(self.current_dest)
        print(f"Info: next location: {self.current_dest}")

    def wait_for_initial_location(self):
        initial_location = self.mqtt.get_location()
        if initial_location is None:
            self.app.after(POLL_INTERVAL_MS, self.wait_for_initial_location)
            return

        print(f"Info: initial location: {initial_location}")
        self.location_nodes.append(initial_location)
        self.last_location_recorded_at = time.monotonic()

        self.route = get_route(initial_location, self.destination)
        print(f"Info: {self.route.distance_str}")
        print(f"Info: {self.route.duration_str}")
        self.route.points = calculate_points_with_difficulty(
            self.route.points, self.difficulty
        )

        self.create_game_screen()

    def create_game_screen(self):
        self.game_start_time = time.monotonic()
        self.wait_text.destroy()

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
        current_location = self.mqtt.get_location()
        if current_location is None:
            self.app.after(POLL_INTERVAL_MS, self.main_game_loop)
            return

        dist = haversine_distance(current_location, self.current_dest)
        print(f"Info: new location: {current_location}; dist: {dist}")

        now = time.monotonic()
        location_recorded = now - self.last_location_recorded_at >= 1
        if location_recorded:
            self.location_nodes.append(current_location)
            self.last_location_recorded_at = now

        if dist < MIN_DIST_M:
            if len(self.route.points) == 0:
                self.arrived(current_location, location_recorded)
                return

            self.set_next_location()

        self.app.after(POLL_INTERVAL_MS, self.main_game_loop)

    def arrived(self, final_location: Point, location_recorded: bool):
        self.mqtt.send_last()

        if not location_recorded:
            self.location_nodes.append(final_location)

        self.start_text.destroy()
        t = time.monotonic() - self.game_start_time
        t0 = self.route.duration
        score = max(
            0,
            round(
                100 * (
                    1 - (
                        math.log10(t / t0) /
                        math.log10(5)
                    )
                )
            )
        )

        self.finished = customtkinter.CTkLabel(
            self.app,
            text=(
                "You did it! 🎉🎉\n\n"
                f"Score: {score}/100"
            ),
            font=("Arial", 18),
        )
        self.finished.place(relx=0.5, rely=0.5, anchor="center")

        self.location_map_path = create_location_map(self.location_nodes)
        self.map_button = customtkinter.CTkButton(
            self.app,
            text="Open route map",
            command=self.open_location_map,
        )
        self.map_button.place(relx=0.5, rely=0.93, anchor="center")
        open_route_map(self.location_map_path)

    def open_location_map(self):
        open_route_map(self.location_map_path)

    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    GeoQuest().run()

