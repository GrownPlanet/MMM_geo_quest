import customtkinter

word = None

app = customtkinter.CTk()
app.title("My App")
app.attributes("-fullscreen", True )
app.title("GeoQuest")

def start_game():
    global word
    word = text_input.get() if text_input.get() else None
    if word:
        print(f"Starting game with word: {word}")
        start.destroy()
        start_text = customtkinter.CTkLabel(app, text=f"Game started with word: {word}, check your Arduino!", font=("Arial", 18))
        start_text.place(relx=0.5, rely=0.5, anchor="center")

title_label = customtkinter.CTkLabel(app, text="Welcome to GeoQuest!", font=("Arial", 24))
text_input = customtkinter.CTkEntry(app, placeholder_text="Enter a word", width=200, height=30, border_width=2, corner_radius=10)
start = customtkinter.CTkButton(app, text="Start Game", command=start_game, width=200, height=30, border_width=2, corner_radius=10)

title_label.place(relx=0.5, rely=0.2, anchor="center")
text_input.place(relx=0.5, rely=0.4, anchor="center")
start.place(relx=0.5, rely=0.5, anchor="center")

app.mainloop()