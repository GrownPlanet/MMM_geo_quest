# MMM GeoQuest

## Setup

- zet de `MAPBOX_TOKEN` in `.env`
- installeer `requirements.txt`: `pip install -r requirements.txt`

## TODO's

### Computer

- [x] korste pad genereren
- [ ] MQTT server communicatie
  - [ ] initiële locatie opvragen
  - [ ] difficulty opvragen

### Arduino

- [ ] MQTT server communicatie
  - [ ] huidige punt ophalen
  - [ ] aankomst aangeven
- [ ] richting naar volgende punt
- [ ] aankomst detecteren
- [ ] richting aangeven op display

## Plan

Kort stappenplan code:

1. naam ingeven
2. hashen
3. omzetten naar locatie binnen Gent
4. route aanvragen
5. moeilijkheid selecteren
6. aantal kruispunten op basis van moeilijkheid
7. volgende punt wordt aan arduino gegeven
8. richting bepalen en weergeven
   - door middel van gps en IMU
9. aan punt gearriveerd? -> naar stap 7
10. aan laatste punt? /Geslaagd!/ score (tijd?) weergeven.

## File structure

- `snippets/`: snippets code die later nog handig kunnen zijn
- `arduino/navigator`: de broncode voor op de arduino
- `computer`: de broncode voor op de computer
- `media`: afbeeldingen voor en over het projects
- `.env`: environment variabelen
- `.env.example`: voorbeeld environment variabelen
