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

word = None
destination = None  # (longitude, latitude) voor Arduino

def start_game():
    global word, destination
    word = text_input.get() if text_input.get() else None
    if word:
        destination = word_to_location(word)
        lon, lat = destination
        print(f"Starting game with word: {word}")
        print(f"Hashed location (lon, lat): {lon:.6f}, {lat:.6f}")
        start.destroy()
        start_text = customtkinter.CTkLabel(
            app,
            text=f"Game started!\nWord: {word}\nDestination: {lon:.6f}, {lat:.6f}\nCheck your Arduino!",
            font=("Arial", 18),
        )
        start_text.place(relx=0.5, rely=0.5, anchor="center")

if __name__ == "__main__":
    app = customtkinter.CTk()
    app.title("My App")
    app.attributes("-fullscreen", True)
    app.title("GeoQuest")
    
    title_label = customtkinter.CTkLabel(app, text="Welcome to GeoQuest!", font=("Arial", 24))
    text_input = customtkinter.CTkEntry(app, placeholder_text="Enter a word", width=200, height=30, border_width=2, corner_radius=10)
    start = customtkinter.CTkButton(app, text="Start Game", command=start_game, width=200, height=30, border_width=2, corner_radius=10)
    
    title_label.place(relx=0.5, rely=0.2, anchor="center")
    text_input.place(relx=0.5, rely=0.4, anchor="center")
    start.place(relx=0.5, rely=0.5, anchor="center")
    
    app.mainloop()
