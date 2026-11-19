# Arduino-navigator uitvoeren

De code toont op het OLED een pijl naar een GPS-waypoint. De IMU bepaalt de
richting van de navigator en compenseert kanteling met de magnetometer-Z-as.

## Benodigde libraries

Installeer deze via **Arduino IDE > Library Manager**:

- Adafruit GPS Library
- Adafruit GFX Library
- Adafruit SSD1306

## GPS aansluiten

De sketch gebruikt D7 als Arduino-TX en D8 als Arduino-RX:

- GPS **TX → D8**
- GPS **RX → D7**
- GPS **GND → Arduino GND**
- GPS-voeding volgens de specificatie van de module

## Stappen

1. Open `arduino/navigator/navigator.ino` in Arduino IDE.
2. Kies **Tools > Board > Arduino Nano 33 BLE Sense Rev2** en
   **Tools > Port > [poort van je Arduino]**.
3. Laat `MAG_CALIBRATION_CONFIGURED` eerst op `false` staan en klik **Upload**.
4. Open **Tools > Serial Monitor**. Kies **115200 baud** en regelafsluiting
   **Newline** of **Both NL & CR**.
5. Typ `CAL` en druk Enter. Draai en kantel de navigator in alle richtingen.
   Typ daarna `CALDONE` en druk Enter.
6. Kopieer de zes getoonde waarden naar `MAG_OFFSET_X/Y/Z` en `MAG_SCALE_X/Y/Z`
   in de sketch. Zet `MAG_CALIBRATION_CONFIGURED` op `true`.
7. Vul indien nodig `MAGNETIC_DECLINATION_DEG` in (oost positief) en pas
   `HEADING_MOUNT_OFFSET_DEG` aan voor de montage. Klik opnieuw **Upload**.
8. Open de Serial Monitor opnieuw op **115200 baud**. Wacht buiten op GPS-fix.
   Typ een waypoint in decimale graden en druk Enter, bijvoorbeeld:
   `WP:51.053700,3.725000`
9. De pijl en afstand verschijnen op het OLED. Typ `CLEAR` om het waypoint te
   wissen. Binnen 15 meter verschijnt `GEARRIVEERD`.

GPS gebruikt 9600 baud; de Serial Monitor gebruikt 115200 baud. Kies bij
**Tools > Port** de poort die bij jouw Arduino hoort.
