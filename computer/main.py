import customtkinter
import hashlib
import math

# Belfort van Gent als centrum
BELFORT_LAT = 51.0537
BELFORT_LON = 3.7250
RADIUS_KM = 3.0

word = None
destination = None  # (longitude, latitude) voor Arduino

app = customtkinter.CTk()
app.title("My App")
app.attributes("-fullscreen", True)
app.title("GeoQuest")


# TODO: deze functie herimplementeren
# 
# Er wordt nu een punt binnen een cirkel gekozen, maar het is geen goede manier
# om een willikeurig punt te kiezen binnen gent. Er is nu namelijk meer kans
# dat het dicht bij het belfort is dan er verder van (verdeling is niet
# volledig uniform)
#
# Ik stel voor dat we een punt binnnen een rechthoek nemen en de 1ste helft van
# het nummer de x-coordinaat laten selecteren en de 2de helft het y-coordinaat.
def word_to_location(word: str) -> tuple[float, float]:
    """Hash het woord en map het naar een punt binnen 3 km rond het Belfort.
    Retourneert (longitude, latitude) klaar voor upload naar Arduino.
    """
    digest = hashlib.sha256(word.encode("utf-8")).digest()

    # Uniforme verdeling in de cirkel via poolcoördinaten
    angle = int.from_bytes(digest[:8], "big") / (2**64) * 2 * math.pi
    r_fraction = math.sqrt(int.from_bytes(digest[8:16], "big") / (2**64))
    distance_km = r_fraction * RADIUS_KM

    # Omzetten van km-offset naar lat/lon
    dlat = (distance_km * math.cos(angle)) / 111.32
    dlon = (distance_km * math.sin(angle)) / (111.32 * math.cos(math.radians(BELFORT_LAT)))

    lat = BELFORT_LAT + dlat
    lon = BELFORT_LON + dlon
    return lon, lat


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


title_label = customtkinter.CTkLabel(app, text="Welcome to GeoQuest!", font=("Arial", 24))
text_input = customtkinter.CTkEntry(app, placeholder_text="Enter a word", width=200, height=30, border_width=2, corner_radius=10)
start = customtkinter.CTkButton(app, text="Start Game", command=start_game, width=200, height=30, border_width=2, corner_radius=10)

title_label.place(relx=0.5, rely=0.2, anchor="center")
text_input.place(relx=0.5, rely=0.4, anchor="center")
start.place(relx=0.5, rely=0.5, anchor="center")

app.mainloop()
