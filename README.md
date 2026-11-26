# MMM GeoQuest

## Spelverloop in het kort

![GeoQuest-spelverloop-in-het-kort](flowchart_kort.svg)

## Technische flowchart

![GeoQuest-technische-flowchart](flowchart_algemeen.svg)

## Setup

- zet de `MAPBOX_TOKEN` in `.env`
- installeer `requirements.txt`: `pip install -r requirements.txt`
- volg [de Arduino-navigator setup](arduino/navigator/README.md) voor de
  boardondersteuning, libraries, ESP8266-bedrading en hotspotconfiguratie

## Hoe uit te voeren

- arduino: zet de gsm-hotspot aan en upload
  `arduino/navigator/navigator.ino` vanuit [Arduino IDE](https://www.arduino.cc/en/software/)
- python: run `python computer/main.py`
- pathfinding server:
  - clone en run [gpath](https://github.com/GrownPlanet/gpath), verdere instructies staan in de readme van dat project

## TODO's

### Computer

- [x] korste pad genereren
- [x] difficulty toepassen
- [x] MQTT server communicatie
  - [x] initiële GPS-locatie ontvangen
  - [x] volgende tussenpunten versturen en locatie-updates verwerken
- [x] difficulty vragen
- [x] main loop
- [ ] aantal punten in easy, medium, hard en expert bespreken
- [ ] grondig testen

### Arduino

- [x] MQTT server communicatie via ESP8266 met AT-firmware
  - [x] GPS-locatie publiceren
  - [x] `NEXT`-tussenpunten en `LAST` ontvangen
- [x] richting naar volgende punt
- [x] aankomst tonen op het OLED (binnen 15 meter)
- [x] richting aangeven op display

### Extra (indien er tijd over is)

- [ ] afgelegde weg tonen

## Communicatie-schema

De Arduino en computer communiceren via MQTT met broker `public.mqttserver.eu`
op poort `1883`. De Arduino heeft hiervoor een ESP8266-module met AT-firmware
nodig en verbindt via een gsm-hotspot. Zie
[arduino/navigator/README.md](arduino/navigator/README.md) voor de hardware- en
library-instellingen.

De Arduino publiceert op `ugent/MMM/GeoQuest/arduino`:

- `LOC<lon>,<lat>`: huidige GPS-locatie, maximaal eenmaal per seconde zolang
  er een GPS-fix en MQTT-verbinding is

De computer publiceert op `ugent/MMM/GeoQuest/computer`:

- `NEXT<lon>,<lat>`: volgend tussenpunt (longitude eerst); de Arduino berekent
  en toont de richting ernaartoe
- `LAST`: de route is voltooid

## Plan

Kort stappenplan code:

1. naam ingeven [x]
2. hashen [x]
3. omzetten naar locatie binnen Gent [x]
4. route aanvragen [x]
5. moeilijkheid selecteren [x]
6. aantal kruispunten op basis van moeilijkheid [x]
7. volgende punt wordt aan Arduino gegeven [x]
8. richting bepalen en weergeven [x]
   - door middel van gps en IMU [x]
9. aankomst bepalen met GPS-locatie-updates -> naar stap 7 [x]
10. aankomst bij het laatste punt tonen [x]

## File structure

- `snippets/`: snippets code die later nog handig kunnen zijn
- `arduino/navigator`: de broncode voor op de arduino
- `computer`: de broncode voor op de computer
- `media`: afbeeldingen voor en over het projects
- `.env`: environment variabelen
- `.env.example`: voorbeeld environment variabelen
