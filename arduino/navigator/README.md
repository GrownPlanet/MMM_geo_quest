# GeoQuest Arduino-navigator

Deze sketch toont op een OLED de richting naar een GPS-waypoint. De pijl is
relatief aan de voorkant van de navigator: draai je het toestel, dan draait de
pijl mee. De GPS-positie bepaalt de richting en afstand naar het waypoint; de
magnetometer en accelerometer van de BMI270/BMM150 bepalen de actuele
toestelrichting. De GPS-positie en richting worden bijgewerkt zodra er een geldige
GPS-fix is. De code controleert aankomst binnen 15 meter.

## Benodigdheden

- Arduino Nano 33 BLE Sense Rev2, of een compatibel bord met BMI270/BMM150 en een
  UART op digitale pinnen 7 en 8.
- GPS-module die NMEA op 9600 baud verstuurt.
- SSD1306-I2C-OLED (128x64, I2C-adres `0x3C`).
- Arduino IDE.

De BMI270/BMM150 is op de Nano 33 BLE Sense Rev2 ingebouwd. Sluit de GPS aan:

| GPS-module | Arduino |
|---|---|
| TX | D8 (Arduino ontvangt GPS-gegevens) |
| RX | D7 (Arduino configureert de GPS) |
| GND | GND |
| Voeding | Volgens de specificatie van de GPS-module |

Sluit de OLED aan op de I2C-pinnen (`SDA`, `SCL`), GND en de geschikte
voedingsspanning. Controleer de spanningslimieten van je bord en modules; sluit
geen 5V-signaal aan op een 3,3V-ingang.

## Eenmalige installatie

1. Installeer Arduino IDE.
2. Open **Tools > Board > Boards Manager** en installeer **Arduino Mbed OS Nano
   Boards**. Selecteer daarna **Arduino Nano 33 BLE Sense Rev2** bij **Tools >
   Board**.
3. Open **Sketch > Include Library > Manage Libraries** en installeer:
   - `Adafruit GPS Library`
   - `Adafruit GFX Library`
   - `Adafruit SSD1306`
4. Open `navigator.ino` in Arduino IDE. Controleer dat de map `navigator` en het
   bestand `navigator.ino` dezelfde sketchnaam hebben.
5. Sluit het bord aan via USB en selecteer de juiste poort bij **Tools > Port**.

## Kompas kalibreren

Kalibreer het magnetisch kompas in de uiteindelijke montage. Met de
standaardinstellingen wordt geen richting getoond totdat een kalibratie is
ingesteld. De kalibratiewaarden zijn afhankelijk van de montage en magnetische
storingen; gebruik dus niet zomaar waarden van een ander toestel.

1. Laat `MAG_CALIBRATION_CONFIGURED` in `navigator.ino` op `false` staan. Upload
   de sketch met **Sketch > Upload** (of de Upload-knop).
2. Open **Tools > Serial Monitor** en stel de baudrate in op **115200**. Kies als
   regelafsluiting **Newline** of **Both NL & CR**.
3. Stuur `CAL` en druk op Enter.
4. Houd het toestel uit de buurt van magneten, staal en sterke stroomvoerende
   kabels. Draai en kantel het langzaam in alle richtingen, zodat alle drie
   magnetometerassen een breed bereik meten. Draai niet alleen plat op tafel.
   Doe dit met de GPS, OLED en overige elektronica op hun normale plaats.
5. Stuur `CALDONE` en druk op Enter. De Serial Monitor toont drie offsets en drie
   schaalfactoren. Bij te weinig meetpunten of een onvolledige draaiing meldt de
   sketch een fout; stuur dan opnieuw `CAL` en herhaal de draaiing.
6. Kopieer de getoonde waarden naar `MAG_OFFSET_X/Y/Z` en `MAG_SCALE_X/Y/Z`
   bovenaan `navigator.ino`. Zet `MAG_CALIBRATION_CONFIGURED` op `true`.
7. Upload de sketch opnieuw. De waarden blijven nu behouden in de sketch na een
   reset. Herhaal de kalibratie als je de sensor of elektronica anders monteert.

De offsets corrigeren een vast magnetisch verschil (hard-iron); de schaalfactoren
compenseren verschillen in meetbereik tussen assen (eenvoudige soft-iron-correctie).
Dit corrigeert geen magnetische storing die tijdens gebruik verandert. Houd de
navigator daarom weg van magneten, staal en stroomvoerende kabels. De
tiltcompensatie gebruikt de accelerometer en is minder betrouwbaar tijdens sterke
beweging of versnelling.

## Noorden en montagehoek instellen

De GPS-bearing is ten opzichte van het ware noorden. De magnetometer meet het
magnetische noorden. Stel `MAGNETIC_DECLINATION_DEG` in op de magnetische
declinatie van de locatie waar je navigeert: oost positief, west negatief.
De standaardwaarde `0.0` is alleen geschikt als de lokale declinatie verwaarloosbaar
is.

Stel `HEADING_MOUNT_OFFSET_DEG` in als de voorwaartse as van de gemonteerde
navigator niet overeenkomt met de sensoras waarop de heading is gebaseerd.
Verander deze offset zo nodig in stappen van 90 graden en controleer met het
toestel vlak en stil, terwijl je het naar bekende kompasrichtingen draait.
Upload de sketch opnieuw na wijzigingen.

## Normaal gebruik

1. Upload de gekalibreerde sketch en open de Serial Monitor op **115200 baud**.
   Gebruik een regelafsluiting met newline.
2. Neem de navigator mee naar buiten of naar een plaats met goed GPS-zicht en
   wacht op een GPS-fix. Zonder geldige GPS-fix verschijnt `GPS: zoeken...` en
   kan er geen pijl naar het doel worden berekend.
3. Stuur een waypoint als `WP:<breedtegraad>,<lengtegraad>` en druk op Enter.
   Gebruik decimale graden en een punt als decimaalteken, bijvoorbeeld:
   `WP:51.053700,3.725000`
4. Wanneer de GPS-fix, het waypoint en de gekalibreerde heading beschikbaar zijn,
   toont de OLED de afstand (`d`), relatieve richting (`rel`) en een pijl. De pijl
   wijst omhoog als het doel recht vooruit ligt; de hoek loopt met de klok mee.
   Binnen 15 meter wordt `GEARRIVEERD` getoond.
5. Stuur `CLEAR` om het waypoint te wissen. Stuur daarna een nieuwe `WP:...` om
   een ander doel in te stellen.

De GPS-module wordt door de sketch op 9600 baud ingesteld. De Serial Monitor
gebruikt 115200 baud voor opdrachten en statusberichten; dit zijn twee
verschillende seriële verbindingen.

## Wat de sketch doet

- Leest GPS-berichten via UART: Arduino D8 ontvangt van GPS TX; Arduino D7 zendt
  configuratie naar GPS RX.
- Berekent de bearing en afstand tussen de actuele GPS-positie en het waypoint.
- Leest versnelling en magnetisch veld van de BMI270/BMM150. Corrigeert de
  magnetometer voor kalibratie, berekent roll en pitch met de accelerometer en
  projecteert het magnetisch veld op het horizontale vlak voor de heading.
- Voegt de montage-offset en magnetische declinatie toe, en dempt snelle
  headingveranderingen met een circulair gemiddelde.
- Toont de relatieve pijl, afstand en heading op het OLED.

De magnetische **Z-component wordt dus wel gebruikt**: `mz` wordt gekalibreerd
en meegenomen in de horizontale projectie (`mxH` en `myH`). Dat is de verticale
veldcorrectie bij kanteling; zonder die term is een kompas alleen bruikbaar als
het bord vrijwel waterpas ligt. Het corrigeert niet voor alle vormen van
magnetische storing.

## Problemen oplossen

- **`IMU kalibreren` op het OLED:** voer de kalibratie hierboven uit, vul de zes
  waarden in en upload opnieuw met `MAG_CALIBRATION_CONFIGURED = true`.
- **`GPS: zoeken...`:** ga naar buiten, controleer de GPS-voeding en controleer
  de TX/RX-aansluitingen (GPS TX naar D8, GPS RX naar D7).
- **Geen OLED:** controleer de I2C-aansluiting en of het OLED-adres `0x3C` is.
- **Pijl wijst consequent een verkeerde richting:** controleer de lokale
  `MAGNETIC_DECLINATION_DEG`, de montagehoek, de kalibratie en magnetische
  storingsbronnen.
- **Pijl schommelt:** houd het toestel stil en horizontaal, beweeg weg van
  magnetische storingsbronnen en houd rekening met GPS-onnauwkeurigheid. Die
  beïnvloedt vooral de bearing dicht bij het waypoint.
