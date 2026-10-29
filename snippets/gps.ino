/*
 * Get the location from the gps and display it on the OLED display
 */


#include <Adafruit_GFX.h>
#include <Adafruit_GPS.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>

UART GPSSerial(digitalPinToPinName(7), digitalPinToPinName(8), NC, NC);
Adafruit_GPS GPS(&GPSSerial);
Adafruit_SSD1306 display(128, 64, &Wire, -1);

const unsigned long REPORT_INTERVAL_MS = 2000;
const unsigned long DATA_TIMEOUT_MS = 3500;
unsigned long lastReportMs = 0;
unsigned long lastPositionUpdateMs = 0;
bool havePositionSentence = false;

void setup() {
  Serial.begin(115200);
  Wire.begin();

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("ERROR: SSD1306 display not found at 0x3C");
    while (true) {
      delay(1000);
    }
  }

  unsigned long waitStart = millis();
  while (!Serial && millis() - waitStart < 3000) {
    delay(10);
  }

  GPS.begin(9600);
  delay(200);
  GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
  delay(200);
  GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);
}

void doublePrint(String message) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(message);
  display.display();

  Serial.println(message);
}

void loop() {
  while (GPSSerial.available() > 0) {
    GPS.read();
    if (GPS.newNMEAreceived()) {
      char *sentence = GPS.lastNMEA();
      if (GPS.parse(sentence)) {
        lastPositionUpdateMs = millis();
        havePositionSentence = true;
      }
    }
  }

  const unsigned long now = millis();
  if (now - lastReportMs < REPORT_INTERVAL_MS) {
    return;
  }
  lastReportMs = now;

  if (!havePositionSentence || now - lastPositionUpdateMs > DATA_TIMEOUT_MS) {
    doublePrint("no data");
  } else if (!GPS.fix) {
    doublePrint("data, wait4fix");
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println(GPS.latitudeDegrees, 6);
    display.println(GPS.longitudeDegrees, 6);
    display.display();

    Serial.println(GPS.latitudeDegrees, 6);
    Serial.println(GPS.longitudeDegrees, 6);
    Serial.println("----------");
  }
}
