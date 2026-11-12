# GeoQuest — User Manual / Gebruikershandleiding

*Choose your language / Kies je taal:*

* [English](#english)

* [Nederlands](#nederlands)

## 🇬🇧 English

### 1. What is GeoQuest?

**GeoQuest** is an interactive outdoor navigation game set in the city of **Ghent** (within a $3 \text{ km} \times 3 \text{ km}$ area around the Belfry). By entering a secret word on your computer, a unique mystery destination is generated. Using your handheld **Arduino Navigator**, you will navigate from waypoint to waypoint using compass directions without relying on a traditional map!

### 2. What You Need

* A **computer** running the GeoQuest desktop application (with an active internet connection).

* The **GeoQuest Arduino Navigator** device (equipped with GPS, IMU/compass, and display, connected to the internet).

### 3. How to Play

#### Step 1: Power Up & Connect

1. Turn on your **Arduino Navigator** outdoors where it has a clear view of the sky so the GPS can lock onto your current location.

2. Launch the **GeoQuest** application on your computer.

#### Step 2: Set Up Your Quest (Word & Difficulty)

1. On the welcome screen, enter any **word** or **name** into the text box (for example, your own name or a random word).

   > *Tip: The same word will always generate the exact same mystery location in Ghent, making it great for challenging friends!*

2. Use the dropdown menu directly below the text box to select your **difficulty level**. Higher difficulties reduce the number of intermediate waypoints along your route, meaning you have to figure out more of the path yourself:

   * **Easy:** All route waypoints included (most frequent guidance).

   * **Medium:** Every 2nd waypoint included (moderate guidance).

   * **Hard:** Every 3rd waypoint included (wider gaps between checkpoints).

   * **Expert:** Every 4th waypoint included (minimal guidance for experienced navigators).

3. Click **"Start Game"**.

#### Step 3: Sync Location & Calculate Route

1. The computer will automatically wait to receive your starting GPS coordinates from your Arduino.

2. Once synced, the computer calculates the walking route, distance, and estimated duration, filters the waypoints based on your chosen difficulty, and sends your first target waypoint to the Arduino.

#### Step 4: Navigate with the Arduino

1. Look at the display on your **Arduino Navigator**. Using its built-in GPS and motion sensors (IMU), it calculates and displays the **direction** you need to walk toward the next waypoint.

2. Hold the device flat and follow the directional indicator on the screen.

3. When you physically reach a waypoint, the Arduino will automatically detect your arrival and request the **next waypoint** from the computer.

#### Step 5: Complete the Quest!

* Continue following the waypoints until you reach the final destination.

* Upon reaching the final point, your Arduino and computer will notify you that you have **succeeded** (*Geslaagd!*) and display your final score/time.

### 4. Troubleshooting

* **Stuck on *"Waiting on current location from arduino..."*:**

  * Make sure your Arduino is powered on and connected to Wi-Fi/internet.

  * Step outside or move away from tall buildings so the GPS module can get a clear satellite fix.

* **Direction arrow seems inaccurate:**

  * Keep the Arduino level (parallel to the ground) and away from strong magnets or large metal objects that could interfere with the IMU compass.

## 🇳🇱 Nederlands

### 1. Wat is GeoQuest?

**GeoQuest** is een interactief outdoor navigatiespel dat zich afspeelt in **Gent** (binnen een gebied van $3 \text{ km} \times 3 \text{ km}$ rond het Belfort). Door een woord in te voeren op je computer wordt een unieke, geheime bestemming gegenereerd. Met je draagbare **Arduino Navigator** wandel je van tussenpunt naar tussenpunt aan de hand van richtingsaanwijzingen, zonder een standaard kaart te gebruiken!

### 2. Wat heb je nodig?

* Een **computer** met de GeoQuest-applicatie (met een actieve internetverbinding).

* De **GeoQuest Arduino Navigator** (uitgerust met GPS, IMU/kompas en scherm, verbonden met het internet).

### 3. Hoe speel je het spel?

#### Stap 1: Opstarten & Verbinden

1. Zet je **Arduino Navigator** buiten aan op een plek met vrij zicht op de lucht, zodat de GPS je huidige locatie kan bepalen.

2. Start de **GeoQuest**-applicatie op je computer.

#### Stap 2: Stel je Quest in (Woord & Moeilijkheidsgraad)

1. Voer op het startscherm een willekeurig **woord** of een **naam** in (bijvoorbeeld je eigen naam of een geheim codewoord).

   > *Tip: Hetzelfde woord levert altijd exact dezelfde bestemming in Gent op. Ideaal om het tegen vrienden op te nemen!*

2. Kies via het keuzemenu onder het tekstvak de gewenste **moeilijkheidsgraad**. Hoe hoger de moeilijkheidsgraad, hoe minder tussenpunten je krijgt, waardoor je een groter deel van de route zelf moet uitzoeken:

   * **Easy:** Alle tussenpunten op de route (maximale begeleiding).

   * **Medium:** Elke 2e tussenpunt (gemiddelde begeleiding).

   * **Hard:** Elke 3e tussenpunt (grotere afstanden tussen controlepunten).

   * **Expert:** Elke 4e tussenpunt (minimale begeleiding voor ervaren navigators).

3. Klik op **"Start Game"**.

#### Stap 3: Synchroniseer locatie & Bereken route

1. De computer wacht nu automatisch tot hij je huidige GPS-locatie van de Arduino ontvangt.

2. Zodra de verbinding compleet is, berekent de computer de wandelroute, afstand en geschatte wandeltijd, filtert de tussenpunten op basis van je gekozen moeilijkheidsgraad en stuurt het eerste tussenpunt door naar je Arduino.

#### Stap 4: Navigeer met de Arduino

1. Kijk op het scherm van je **Arduino Navigator**. Met behulp van de GPS en bewegingssensoren (IMU) berekent en toont het apparaat de **richting** waarin je moet lopen.

2. Houd het apparaat horizontaal en volg de richtingspijl op het scherm.

3. Zodra je aankomt bij een tussenpunt, detecteert de Arduino dit automatisch en vraagt hij het **volgende tussenpunt** op bij de computer.

#### Stap 5: Voltooi de Quest!

* Blijf de tussenpunten volgen totdat je de eindbestemming bereikt.

* Bij aankomst op het laatste punt krijg je de melding **Geslaagd!** en wordt je eindscore (zoals je totale tijd) weergegeven.

### 4. Veelvoorkomende problemen (Troubleshooting)

* **Het scherm blijft hangen op *"Waiting on current location from arduino..."*:**

  * Controleer of de Arduino aanstaat en verbonden is met het internet.

  * Ga naar buiten of weg van hoge gebouwen zodat de GPS-module een goed satellietsignaal kan ontvangen.

* **De richtingspijl wijst niet de juiste kant op:**

  * Houd de Arduino zo vlak mogelijk (evenwijdig aan de grond) en uit de buurt van magneten of grote metalen voorwerpen die het kompas (IMU) kunnen verstoren.