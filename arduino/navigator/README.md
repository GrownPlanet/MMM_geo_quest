# Arduino-navigator uitvoeren

De navigator toont op het OLED een pijl naar het volgende GPS-tussenpunt. De
Nano 33 BLE Sense Rev2 bepaalt de richting met de IMU en GPS. Een aangesloten
ESP8266 met AT-firmware verbindt de Arduino via een gsm-hotspot met MQTT.

## Benodigd

### Hardware

- Arduino Nano 33 BLE Sense Rev2
- ESP8266-module met door WiFiEspAT ondersteunde AT-firmware
- GPS-module en SSD1306 OLED
- Momentane drukknop
- Gsm-hotspot op 2,4 GHz met WPA2-Personal (geen 5 GHz of WPA3-only)

De ESP8266-module werkt hier als Wi-Fi-modem met AT-firmware; de navigator
gebruikt de ESP8266 niet als apart Arduino-board waarop deze sketch draait.

### Boardpakket en libraries

Installeer het boardpakket **Arduino Mbed OS Nano Boards** via **Arduino IDE >
Boards Manager** en kies **Arduino Nano 33 BLE Sense Rev2**.

Installeer deze libraries via **Arduino IDE > Library Manager**:

- Adafruit GPS Library
- Adafruit GFX Library
- Adafruit BusIO (dependency van Adafruit GFX)
- Adafruit SSD1306
- Arduino_BMI270_BMM150
- WiFiEspAT
- PubSubClient

`Wire`, `math`, `stdlib` en `string` zijn onderdeel van de Arduino/core-toolchain
en hoeven niet apart geinstalleerd te worden.

## Aansluiten

De GPS gebruikt een aparte UART:

- GPS **TX -> Arduino D8**
- GPS **RX -> Arduino D7**
- GPS **GND -> Arduino GND**
- GPS-voeding volgens de specificatie van de module

De ESP8266 gebruikt `Serial1`:

- ESP8266 **TX -> Arduino D0 (RX)**
- ESP8266 **RX -> Arduino D1 (TX)**
- ESP8266 **GND -> Arduino GND**
- Voed de ESP8266 met een stabiele 3,3 V-voeding die de stroompieken van de
  module aankan. Gebruik 3,3 V-logicaniveaus.

Sluit de drukknop aan tussen **D2** en **GND**. De sketch gebruikt de interne
pull-up; de resetknop op het board kan niet als invoerknop worden gebruikt.

De sketch verwacht dat de ESP8266 AT-firmware op **115200 baud** staat. De
GPS gebruikt 9600 baud.

## MQTT-berichten

De broker is `public.mqttserver.eu` op poort `1883`.

| Richting | Topic | Payload | Betekenis |
| --- | --- | --- | --- |
| Arduino -> computer | `ugent/MMM/GeoQuest/arduino` | `LOC<lon>,<lat>` | Huidige GPS-locatie; maximaal eenmaal per seconde |
| Computer -> Arduino | `ugent/MMM/GeoQuest/computer` | `NEXT<lon>,<lat>` | Nieuw tussenpunt; longitude komt eerst |
| Computer -> Arduino | `ugent/MMM/GeoQuest/computer` | `LAST` | Route is voltooid |

De Arduino publiceert `LOC` zodra er een GPS-fix en MQTT-verbinding zijn. De
computer gebruikt de locatie om de route te starten en bepaalt aan de hand van
latere locatieberichten wanneer het volgende tussenpunt nodig is. De navigator
berekent zelf de richting naar ieder ontvangen `NEXT`-punt. Het OLED toont
`TUSSENPUNT BEREIKT` gedurende 1,5 seconde binnen 7,5 meter van het huidige
punt; daarna verschijnt de pijl opnieuw. De computer stuurt het volgende
tussenpunt zodra de locatie binnen 15 meter valt.

## Configureren en uploaden

1. Verbind de ESP8266 zoals hierboven beschreven en controleer dat de module
   compatibele AT-firmware heeft.
2. Vul in `navigator.ino` `WIFI_SSID` en `WIFI_PASSWORD` in met de naam en het
   wachtwoord van de gsm-hotspot. Bewaar persoonlijke gegevens lokaal; commit
   ze niet naar de repository.
3. Kies **Tools > Board > Arduino Nano 33 BLE Sense Rev2** en de juiste
   **Tools > Port**.
4. Zet de gsm-hotspot aan en start de computerapplicatie (`python computer/main.py`).
5. Kalibreer zonder Serial Monitor: druk op de knop op D2 om te starten. Draai
   de navigator rustig in alle richtingen; het OLED toont de voortgang. Druk
   dezelfde knop opnieuw om te stoppen. Het OLED meldt of de kalibratie gelukt
   is of dat je langer/vollediger moet draaien.
   De nieuwe waarden gelden direct tot de Arduino wordt gereset; daarna worden
   de kalibratieconstanten uit de sketch geladen.
6. Wacht buiten op GPS-fix. Het OLED toont de GPS-, Wi-Fi- en MQTT-status.
   Zodra de computer de eerste locatie ontvangt, stuurt die automatisch het
   eerste `NEXT`-tussenpunt en verschijnen de pijl en afstand.
7. Controleer de pijl met een actief tussenpunt: draai de navigator op dezelfde
   plaats met de klok mee. `Hdg` moet toenemen en de pijl moet op het OLED
   tegen de klok in meedraaien, zodat hij naar hetzelfde vaste tussenpunt blijft
   wijzen.

Voor standalone testen zonder MQTT kun je via Serial Monitor nog steeds
`WP:<lat>,<lon>` sturen, bijvoorbeeld `WP:51.053700,3.725000`. `CLEAR` wist het
handmatige waypoint. De Serial Monitor is optioneel; `CAL` en `CALDONE` blijven
beschikbaar als alternatieve manier om de kalibratie te starten en te stoppen.

## Problemen met Wi-Fi

Bij een mislukte verbinding controleert de sketch de verbinding elke 10
seconden en toont `WiFi.begin`, `WiFi.status` en `ESP8266 AT error` in de Serial
Monitor. Controleer daarnaast dat de SSID en het wachtwoord exact overeenkomen,
de hotspot zichtbaar is en de ESP8266 een stabiele 3,3 V-voeding met voldoende
stroom krijgt. Deel bij het vragen om hulp alleen deze statusregels, nooit het
hotspotwachtwoord.
