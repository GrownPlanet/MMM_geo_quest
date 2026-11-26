/*
 * GeoQuest navigator
 *
 * - Ontvangt tussenpunten via MQTT: NEXT<lon>,<lat>
 * - Publiceert de GPS-locatie via MQTT: LOC<lon>,<lat>
 * - Leest eigen positie via GPS (bearing maximaal elke seconde herberekenen)
 * - Tussen GPS-updates: heading via BMI270/BMM150 (tilt-compensatie + smoothing)
 * - Toont relatieve pijl naar het doel op OLED
 */

#include <Wire.h>
#include <math.h>
#include <Adafruit_GPS.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino_BMI270_BMM150.h>
#include <WiFiEspAT.h>
#include <PubSubClient.h>
#include <stdlib.h>
#include <string.h>

// --- Hardware ---
UART GPSSerial(digitalPinToPinName(7), digitalPinToPinName(8), NC, NC);
Adafruit_GPS GPS(&GPSSerial);
Adafruit_SSD1306 display(128, 64, &Wire, -1);

// ESP8266 AT-module is connected to Serial1 (D0=RX, D1=TX).
const unsigned long ESP8266_BAUD = 115200;
const char WIFI_SSID[] = "123test";
const char WIFI_PASSWORD[] = "12345test";
const char MQTT_BROKER[] = "public.mqttserver.eu";
const uint16_t MQTT_PORT = 1883;
const char MQTT_OUT_TOPIC[] = "ugent/MMM/GeoQuest/arduino";
const char MQTT_IN_TOPIC[] = "ugent/MMM/GeoQuest/computer";
const unsigned long NETWORK_RETRY_INTERVAL_MS = 10000;
const unsigned long LOCATION_PUBLISH_INTERVAL_MS = 1000;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// --- Timing ---
const unsigned long GPS_BEARING_INTERVAL_MS = 1000;
const unsigned long GPS_DATA_TIMEOUT_MS = 3500;
const unsigned long DISPLAY_INTERVAL_MS = 200;
const float ARRIVAL_RADIUS_M = 7.5f;
const float HEADING_SMOOTH_ALPHA = 0.18f;  // lager = stabieler, trager
// Draai heading zodat "vooruit" = pijl omhoog (pas aan per montage, bv. 90/180)
const float HEADING_MOUNT_OFFSET_DEG = 0.0f;
// Kompasheading hoort met de klok mee toe te nemen; keer de Y-as om voor deze sensororiëntatie.
const bool HEADING_REVERSE_Y = true;
// Oostelijke magnetische declinatie is positief. Stel in voor de speelregio.
const float MAGNETIC_DECLINATION_DEG = 2.44f;  // Centrum Gent, WMM-2025 (19-11-2026)

// Vul deze waarden in met de uitvoer van CAL/CALDONE en zet daarna op true.
const bool MAG_CALIBRATION_CONFIGURED = true;
const float MAG_OFFSET_X = 56.5f;
const float MAG_OFFSET_Y = -19.0f;
const float MAG_OFFSET_Z = -41.5f;
const float MAG_SCALE_X = 0.9597f;
const float MAG_SCALE_Y = 1.0155f;
const float MAG_SCALE_Z = 1.0275f;

// --- Waypoint / GPS state ---
bool haveTarget = false;
bool routeComplete = false;
float targetLat = 0.0f;
float targetLon = 0.0f;

bool haveFix = false;
bool havePositionSentence = false;
float currentLat = 0.0f;
float currentLon = 0.0f;

float bearingToTargetDeg = 0.0f;  // absolute, true north
float distanceToTargetM = 0.0f;
bool haveBearing = false;

unsigned long lastPositionUpdateMs = 0;
unsigned long lastBearingUpdateMs = 0;
unsigned long lastDisplayMs = 0;
unsigned long lastWiFiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;
unsigned long lastLocationPublishMs = 0;
bool hasPublishedLocation = false;
bool wifiModuleReady = false;

// --- IMU / heading ---
float headingDeg = 0.0f;          // 0..360, device forward vs true north
bool haveHeading = false;

float magOffsetX = MAG_OFFSET_X;
float magOffsetY = MAG_OFFSET_Y;
float magOffsetZ = MAG_OFFSET_Z;
float magScaleX = MAG_SCALE_X;
float magScaleY = MAG_SCALE_Y;
float magScaleZ = MAG_SCALE_Z;
bool haveMagCalibration = MAG_CALIBRATION_CONFIGURED;
bool magCalibrationRunning = false;
bool magCalibrationHasSample = false;
unsigned long magCalibrationSamples = 0;
float magMinX, magMinY, magMinZ;
float magMaxX, magMaxY, magMaxZ;

// Serial command buffer
String serialLine;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

float wrap360(float deg) {
  while (deg < 0.0f) deg += 360.0f;
  while (deg >= 360.0f) deg -= 360.0f;
  return deg;
}

/** Kleinste verschil a - b in (-180, 180]. */
float angleDiffDeg(float a, float b) {
  float d = wrap360(a) - wrap360(b);
  if (d > 180.0f) d -= 360.0f;
  if (d <= -180.0f) d += 360.0f;
  return d;
}

float degToRad(float deg) { return deg * (PI / 180.0f); }
float radToDeg(float rad) { return rad * (180.0f / PI); }

/** Initial bearing van punt A naar B (graden t.o.v. true north). */
float calculateBearingDeg(float lat1, float lon1, float lat2, float lon2) {
  float phi1 = degToRad(lat1);
  float phi2 = degToRad(lat2);
  float dLon = degToRad(lon2 - lon1);

  float y = sin(dLon) * cos(phi2);
  float x = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(dLon);
  return wrap360(radToDeg(atan2(y, x)));
}

/** Haversine-afstand in meters. */
float calculateDistanceM(float lat1, float lon1, float lat2, float lon2) {
  const float R = 6371000.0f;
  float dLat = degToRad(lat2 - lat1);
  float dLon = degToRad(lon2 - lon1);
  float a = sin(dLat / 2) * sin(dLat / 2) +
            cos(degToRad(lat1)) * cos(degToRad(lat2)) *
                sin(dLon / 2) * sin(dLon / 2);
  float c = 2.0f * atan2(sqrt(a), sqrt(1.0f - a));
  return R * c;
}

void showBootMessage(const char *msg) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 24);
  display.println(msg);
  display.display();
  Serial.println(msg);
}

// ---------------------------------------------------------------------------
// MQTT: waypoint ontvangen en GPS-locatie publiceren
// ---------------------------------------------------------------------------

void handleMqttMessage(char *topic, byte *payload, unsigned int length) {
  if (strcmp(topic, MQTT_IN_TOPIC) != 0) return;

  String message;
  message.reserve(length);
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  message.trim();

  if (message == "LAST") {
    haveTarget = false;
    haveBearing = false;
    routeComplete = true;
    Serial.println("MQTT: LAST");
    return;
  }

  if (!message.startsWith("NEXT")) {
    Serial.print("ERROR: unknown MQTT message: ");
    Serial.println(message);
    return;
  }

  String coordinates = message.substring(4);
  int comma = coordinates.indexOf(',');
  if (comma <= 0 || comma >= (int)coordinates.length() - 1) {
    Serial.println("ERROR: MQTT NEXT format; expected NEXT<lon>,<lat>");
    return;
  }

  String longitude = coordinates.substring(0, comma);
  String latitude = coordinates.substring(comma + 1);
  char *lonEnd;
  char *latEnd;
  float lon = strtof(longitude.c_str(), &lonEnd);
  float lat = strtof(latitude.c_str(), &latEnd);
  if (lonEnd == longitude.c_str() || *lonEnd != '\0' ||
      latEnd == latitude.c_str() || *latEnd != '\0' ||
      !isfinite(lon) || !isfinite(lat) ||
      lat < -90.0f || lat > 90.0f || lon < -180.0f || lon > 180.0f) {
    Serial.println("ERROR: MQTT NEXT coordinates invalid or out of range");
    return;
  }

  targetLat = lat;
  targetLon = lon;
  haveTarget = true;
  routeComplete = false;
  haveBearing = false;
  lastBearingUpdateMs = 0;
  Serial.print("MQTT: NEXT ");
  Serial.print(targetLon, 6);
  Serial.print(",");
  Serial.println(targetLat, 6);
}

const char *wifiStatusName(int status) {
  switch (status) {
    case WL_NO_MODULE: return "NO_MODULE";
    case WL_IDLE_STATUS: return "IDLE";
    case WL_NO_SSID_AVAIL: return "NO_SSID";
    case WL_CONNECTED: return "CONNECTED";
    case WL_CONNECT_FAILED: return "CONNECT_FAILED";
    case WL_CONNECTION_LOST: return "CONNECTION_LOST";
    case WL_DISCONNECTED: return "DISCONNECTED";
    default: return "UNKNOWN";
  }
}

const char *wifiDriverErrorName(EspAtDrvError error) {
  switch (error) {
    case EspAtDrvError::NO_ERROR: return "NO_ERROR";
    case EspAtDrvError::NOT_INITIALIZED: return "NOT_INITIALIZED";
    case EspAtDrvError::AT_NOT_RESPONDIG: return "AT_NOT_RESPONDING";
    case EspAtDrvError::AT_ERROR: return "AT_ERROR";
    case EspAtDrvError::NO_AP: return "NO_AP";
    case EspAtDrvError::LINK_ALREADY_CONNECTED: return "LINK_ALREADY_CONNECTED";
    case EspAtDrvError::LINK_NOT_ACTIVE: return "LINK_NOT_ACTIVE";
    case EspAtDrvError::RECEIVE: return "RECEIVE";
    case EspAtDrvError::SEND: return "SEND";
    case EspAtDrvError::UDP_BUSY: return "UDP_BUSY";
    case EspAtDrvError::UDP_LARGE: return "UDP_LARGE";
    case EspAtDrvError::UDP_TIMEOUT: return "UDP_TIMEOUT";
    default: return "UNKNOWN";
  }
}

void maintainMqttConnection() {
  const unsigned long now = millis();

  if (!wifiModuleReady) {
    if (lastWiFiAttemptMs == 0 ||
        now - lastWiFiAttemptMs >= NETWORK_RETRY_INTERVAL_MS) {
      lastWiFiAttemptMs = now;
      Serial.println("Initializing ESP8266 AT module...");
      wifiModuleReady = WiFi.init(Serial1);
      if (!wifiModuleReady) {
        Serial.println("ERROR: ESP8266 AT module not responding; will retry");
        return;
      }
      lastWiFiAttemptMs = 0;
    } else {
      return;
    }
  }

  if (WiFi.status() != WL_CONNECTED) {
    if (mqttClient.connected()) mqttClient.disconnect();

    if (lastWiFiAttemptMs == 0 ||
        now - lastWiFiAttemptMs >= NETWORK_RETRY_INTERVAL_MS) {
      lastWiFiAttemptMs = now;
      Serial.println("Connecting to phone hotspot...");
      int beginStatus = WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      EspAtDrvError driverError = WiFi.getLastDriverError();
      int currentStatus = WiFi.status();

      Serial.print("WiFi.begin: ");
      Serial.println(wifiStatusName(beginStatus));
      Serial.print("WiFi.status: ");
      Serial.println(wifiStatusName(currentStatus));
      Serial.print("ESP8266 AT error: ");
      Serial.println(wifiDriverErrorName(driverError));

      if (currentStatus == WL_CONNECTED) {
        Serial.println("WiFi connected");
      } else {
        Serial.println("ERROR: WiFi connection failed; will retry in 10 seconds");
      }
    }
    return;
  }

  if (!mqttClient.connected()) {
    if (lastMqttAttemptMs == 0 ||
        now - lastMqttAttemptMs >= NETWORK_RETRY_INTERVAL_MS) {
      lastMqttAttemptMs = now;
      Serial.println("Connecting to MQTT broker...");
      if (mqttClient.connect("GeoQuestNavigator")) {
        if (mqttClient.subscribe(MQTT_IN_TOPIC)) {
          Serial.println("MQTT connected and subscribed");
          hasPublishedLocation = false;
        } else {
          Serial.println("ERROR: MQTT subscribe failed");
          mqttClient.disconnect();
        }
      } else {
        Serial.print("ERROR: MQTT connection failed, state ");
        Serial.println(mqttClient.state());
      }
    }
    return;
  }

  mqttClient.loop();
}

void publishCurrentLocation() {
  if (!haveFix || !mqttClient.connected()) return;

  const unsigned long now = millis();
  if (hasPublishedLocation &&
      now - lastLocationPublishMs < LOCATION_PUBLISH_INTERVAL_MS) {
    return;
  }
  lastLocationPublishMs = now;

  char payload[40];
  snprintf(payload, sizeof(payload), "LOC%.6f,%.6f", currentLon, currentLat);
  if (mqttClient.publish(MQTT_OUT_TOPIC, payload)) {
    hasPublishedLocation = true;
    Serial.print("MQTT: ");
    Serial.println(payload);
  } else {
    Serial.println("ERROR: MQTT location publish failed");
  }
}

// ---------------------------------------------------------------------------
// Serial: waypoint ontvangen
// Protocol:  WP:<lat>,<lon>     bv. WP:51.053700,3.725000
// Optioneel: CLEAR              wis waypoint
//           CAL                start magnetometerkalibratie
//           CALDONE            stop en toon kalibratiewaarden
// ---------------------------------------------------------------------------

void handleSerialLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line.equalsIgnoreCase("CLEAR")) {
    haveTarget = false;
    routeComplete = false;
    haveBearing = false;
    Serial.println("OK CLEAR");
    return;
  }

  if (line.equalsIgnoreCase("CAL")) {
    magCalibrationRunning = true;
    magCalibrationHasSample = false;
    magCalibrationSamples = 0;
    Serial.println("MAG CAL started: rotate the device in all orientations, then send CALDONE");
    return;
  }

  if (line.equalsIgnoreCase("CALDONE")) {
    if (!magCalibrationRunning) {
      Serial.println("ERR MAG CAL not running");
      return;
    }
    magCalibrationRunning = false;

    if (magCalibrationSamples < 100 || !magCalibrationHasSample) {
      Serial.println("ERR MAG CAL too few samples; send CAL and try again");
      return;
    }

    const float rangeX = (magMaxX - magMinX) * 0.5f;
    const float rangeY = (magMaxY - magMinY) * 0.5f;
    const float rangeZ = (magMaxZ - magMinZ) * 0.5f;
    if (rangeX < 5.0f || rangeY < 5.0f || rangeZ < 5.0f) {
      Serial.println("ERR MAG CAL incomplete rotation; each axis range must be at least 10 uT");
      return;
    }

    magOffsetX = (magMaxX + magMinX) * 0.5f;
    magOffsetY = (magMaxY + magMinY) * 0.5f;
    magOffsetZ = (magMaxZ + magMinZ) * 0.5f;
    const float averageRange = (rangeX + rangeY + rangeZ) / 3.0f;
    magScaleX = averageRange / rangeX;
    magScaleY = averageRange / rangeY;
    magScaleZ = averageRange / rangeZ;
    haveMagCalibration = true;

    Serial.println("MAG CAL values (copy to the constants in navigator.ino):");
    Serial.print("MAG_OFFSET_X = "); Serial.println(magOffsetX, 4);
    Serial.print("MAG_OFFSET_Y = "); Serial.println(magOffsetY, 4);
    Serial.print("MAG_OFFSET_Z = "); Serial.println(magOffsetZ, 4);
    Serial.print("MAG_SCALE_X = "); Serial.println(magScaleX, 4);
    Serial.print("MAG_SCALE_Y = "); Serial.println(magScaleY, 4);
    Serial.print("MAG_SCALE_Z = "); Serial.println(magScaleZ, 4);
    Serial.println("Set MAG_CALIBRATION_CONFIGURED to true, then upload again to keep them after reboot.");
    return;
  }

  if (line.startsWith("WP:") || line.startsWith("wp:")) {
    String payload = line.substring(3);
    int comma = payload.indexOf(',');
    if (comma < 0) {
      Serial.println("ERR WP format");
      return;
    }
    float lat = payload.substring(0, comma).toFloat();
    float lon = payload.substring(comma + 1).toFloat();
    if (lat < -90.0f || lat > 90.0f || lon < -180.0f || lon > 180.0f) {
      Serial.println("ERR WP range");
      return;
    }
    targetLat = lat;
    targetLon = lon;
    haveTarget = true;
    routeComplete = false;
    haveBearing = false;  // force herberekening bij volgende GPS-cycle
    lastBearingUpdateMs = 0;
    Serial.print("OK WP ");
    Serial.print(targetLat, 6);
    Serial.print(",");
    Serial.println(targetLon, 6);
    return;
  }

  Serial.println("ERR unknown cmd");
}

void pollSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialLine.length() > 0) {
        handleSerialLine(serialLine);
        serialLine = "";
      }
    } else {
      if (serialLine.length() < 80) {
        serialLine += c;
      }
    }
  }
}

// ---------------------------------------------------------------------------
// GPS
// ---------------------------------------------------------------------------

void pollGPS() {
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
  if (!havePositionSentence || now - lastPositionUpdateMs > GPS_DATA_TIMEOUT_MS) {
    haveFix = false;
    return;
  }

  if (!GPS.fix) {
    haveFix = false;
    return;
  }

  currentLat = GPS.latitudeDegrees;
  currentLon = GPS.longitudeDegrees;
  haveFix = true;
}

void updateBearingFromGPS() {
  if (!haveFix || !haveTarget) return;

  const unsigned long now = millis();
  if (haveBearing && (now - lastBearingUpdateMs < GPS_BEARING_INTERVAL_MS)) {
    return;
  }

  bearingToTargetDeg = calculateBearingDeg(currentLat, currentLon, targetLat, targetLon);
  distanceToTargetM = calculateDistanceM(currentLat, currentLon, targetLat, targetLon);
  haveBearing = true;
  lastBearingUpdateMs = now;

  Serial.print("BEARING ");
  Serial.print(bearingToTargetDeg, 1);
  Serial.print(" deg  DIST ");
  Serial.print(distanceToTargetM, 1);
  Serial.println(" m");
}

// ---------------------------------------------------------------------------
// IMU heading (tilt-compensatie + circulaire EMA-smoothing)
// ---------------------------------------------------------------------------

void updateHeadingFromIMU() {
  if (!IMU.accelerationAvailable() || !IMU.magneticFieldAvailable()) {
    return;
  }

  float ax, ay, az;
  float mx, my, mz;
  IMU.readAcceleration(ax, ay, az);
  IMU.readMagneticField(mx, my, mz);

  if (magCalibrationRunning) {
    if (!magCalibrationHasSample) {
      magMinX = magMaxX = mx;
      magMinY = magMaxY = my;
      magMinZ = magMaxZ = mz;
      magCalibrationHasSample = true;
    } else {
      magMinX = min(magMinX, mx);
      magMinY = min(magMinY, my);
      magMinZ = min(magMinZ, mz);
      magMaxX = max(magMaxX, mx);
      magMaxY = max(magMaxY, my);
      magMaxZ = max(magMaxZ, mz);
    }
    magCalibrationSamples++;
    return;
  }

  if (!haveMagCalibration) {
    return;
  }

  mx -= magOffsetX;
  my -= magOffsetY;
  mz -= magOffsetZ;
  mx *= magScaleX;
  my *= magScaleY;
  mz *= magScaleZ;

  // Roll / pitch uit accelerometer (rad)
  float roll = atan2(ay, az);
  float pitch = atan2(-ax, sqrt(ay * ay + az * az));

  // Tilt-gecompenseerde magnetometer in horizontaal vlak
  float cosR = cos(roll);
  float sinR = sin(roll);
  float cosP = cos(pitch);
  float sinP = sin(pitch);

  float mxH = mx * cosP + mz * sinP;
  float myH = mx * sinR * sinP + my * cosR - mz * sinR * cosP;

  // Heading is clockwise-positive; de Y-as van deze sensororiëntatie heeft het tegengestelde teken.
  float headingY = HEADING_REVERSE_Y ? -myH : myH;
  float rawHeading = wrap360(radToDeg(atan2(headingY, mxH)) +
                             HEADING_MOUNT_OFFSET_DEG +
                             MAGNETIC_DECLINATION_DEG);

  if (!haveHeading) {
    headingDeg = rawHeading;
    haveHeading = true;
  } else {
    // Circulaire exponential moving average
    float delta = angleDiffDeg(rawHeading, headingDeg);
    headingDeg = wrap360(headingDeg + HEADING_SMOOTH_ALPHA * delta);
  }
}

// ---------------------------------------------------------------------------
// Display: relatieve pijl
// ---------------------------------------------------------------------------

void drawArrow(int cx, int cy, float relativeDeg, int length) {
  // 0° = recht vooruit (omhoog op scherm), hoek loopt met de klok mee
  float rad = degToRad(relativeDeg);
  float tipX = cx + length * sin(rad);
  float tipY = cy - length * cos(rad);

  // Basis loodrecht op de pijlrichting
  float backX = cx - (length * 0.35f) * sin(rad);
  float backY = cy + (length * 0.35f) * cos(rad);
  float orthoX = (length * 0.45f) * cos(rad);
  float orthoY = (length * 0.45f) * sin(rad);

  int x0 = (int)(tipX + 0.5f);
  int y0 = (int)(tipY + 0.5f);
  int x1 = (int)(backX + orthoX + 0.5f);
  int y1 = (int)(backY + orthoY + 0.5f);
  int x2 = (int)(backX - orthoX + 0.5f);
  int y2 = (int)(backY - orthoY + 0.5f);

  display.fillTriangle(x0, y0, x1, y1, x2, y2, SSD1306_WHITE);
  display.drawLine(cx, cy, x0, y0, SSD1306_WHITE);
}

void updateDisplay() {
  const unsigned long now = millis();
  if (now - lastDisplayMs < DISPLAY_INTERVAL_MS) return;
  lastDisplayMs = now;

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);

  if (!haveTarget) {
    display.println(routeComplete ? "Route voltooid" : "Wacht op NEXT...");
    display.display();
    return;
  }

  if (!haveFix) {
    display.println("GPS: zoeken...");
    display.print("Doel ");
    display.print(targetLat, 4);
    display.display();
    return;
  }

  if (magCalibrationRunning) {
    display.println("IMU kalibreren...");
    display.display();
    return;
  }

  if (!haveMagCalibration) {
    display.println("IMU kalibreren");
    display.println("Serial: CAL");
    display.display();
    return;
  }

  if (!haveHeading || !haveBearing) {
    display.println("Sensors...");
    display.display();
    return;
  }

  float relative = angleDiffDeg(bearingToTargetDeg, headingDeg);
  bool arrived = distanceToTargetM <= ARRIVAL_RADIUS_M;

  if (arrived) {
    display.setTextSize(2);
    display.setCursor(10, 24);
    display.println("GEARRIVEERD");
    display.display();
    return;
  }

  // Info links
  display.print("d=");
  if (distanceToTargetM >= 1000.0f) {
    display.print(distanceToTargetM / 1000.0f, 2);
    display.println("km");
  } else {
    display.print((int)distanceToTargetM);
    display.println("m");
  }

  display.print("rel=");
  display.print(relative, 0);
  display.println(" deg");

  // Pijl rechts-centraal
  drawArrow(96, 36, relative, 22);

  // Klein kompas-hint
  display.setCursor(0, 56);
  display.print("Hdg ");
  display.print(headingDeg, 0);

  display.display();
}

// ---------------------------------------------------------------------------
// Setup / loop
// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  Wire.begin();

  unsigned long waitStart = millis();
  while (!Serial && millis() - waitStart < 3000) {
    delay(10);
  }

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("ERROR: SSD1306 not found at 0x3C");
    while (true) delay(1000);
  }
  showBootMessage("GeoQuest boot");

  if (!IMU.begin()) {
    showBootMessage("IMU error");
    while (true) delay(100);
  }

  GPS.begin(9600);
  delay(200);
  GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
  delay(200);
  GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);

  Serial1.begin(ESP8266_BAUD);
  wifiModuleReady = WiFi.init(Serial1);
  if (!wifiModuleReady) {
    Serial.println("ERROR: ESP8266 AT module not responding; will retry");
  }
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(handleMqttMessage);

  showBootMessage("Navigator OK");
  delay(800);
  Serial.println("READY");
  Serial.println("Waiting for MQTT NEXT<lon>,<lat>");
  if (!haveMagCalibration) {
    Serial.println("Magnetometer not calibrated. Send CAL, rotate in all orientations, then send CALDONE.");
  }
}

void loop() {
  pollSerial();
  pollGPS();
  maintainMqttConnection();
  publishCurrentLocation();
  updateHeadingFromIMU();
  updateBearingFromGPS();
  updateDisplay();
}
