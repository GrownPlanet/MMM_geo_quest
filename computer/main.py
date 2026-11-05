import customtkinter
import hashlib
import math

# Belfort van Gent als centrum
BELFORT_LAT = 51.0537
BELFORT_LON = 3.7250

AREA_SIZE_KM = 3.0
HALF_AREA_KM = AREA_SIZE_KM / 2

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
    def __init__(self):
        self.word = None
        self.destination = None

        self.app = customtkinter.CTk()
        self.app.title("GeoQuest")
        self.app.attributes("-fullscreen", True)

        self.create_start_screen()

    def create_start_screen(self):
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

        self.title_label.place(relx=0.5, rely=0.2, anchor="center")
        self.text_input.place(relx=0.5, rely=0.4, anchor="center")
        self.start_button.place(relx=0.5, rely=0.5, anchor="center")

    def start_game(self):
        word = self.text_input.get()

        if not word:
            return

        self.word = word
        self.destination = word_to_location(word)

        lon, lat = self.destination

        print(f"Starting game with word: {self.word}")
        print(f"Hashed location (lon, lat): {lon:.6f}, {lat:.6f}")

        self.create_game_screen(lon, lat)

    def create_game_screen(self, lon, lat):
        self.start_button.destroy()
        self.text_input.destroy()
        self.title_label.destroy()

        self.start_text = customtkinter.CTkLabel(
            self.app,
            text=(
                f"Game started!\n"
                f"Word: {self.word}\n"
                f"Destination: {lon:.6f}, {lat:.6f}\n"
                f"Check your Arduino!"
            ),
            font=("Arial", 18)
        )

        self.start_text.place(relx=0.5, rely=0.5, anchor="center")

    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    game = GeoQuest()
    game.run()
