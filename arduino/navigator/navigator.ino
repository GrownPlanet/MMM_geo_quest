/*
 * GeoQuest navigator
 *
 * - Ontvangt tussenpunt via Serial:  WP:<lat>,<lon>
 * - Leest eigen positie via GPS (elke ~3 s bearing herberekenen)
 * - Tussen GPS-updates: heading via BMI270/BMM150 (tilt-compensatie + smoothing)
 * - Toont relatieve pijl naar het doel op OLED
 */

#include <Wire.h>
#include <math.h>
#include <Adafruit_GPS.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Arduino_BMI270_BMM150.h>

// --- Hardware ---
UART GPSSerial(digitalPinToPinName(7), digitalPinToPinName(8), NC, NC);
Adafruit_GPS GPS(&GPSSerial);
Adafruit_SSD1306 display(128, 64, &Wire, -1);

// --- Timing ---
const unsigned long GPS_BEARING_INTERVAL_MS = 3000;
const unsigned long GPS_DATA_TIMEOUT_MS = 3500;
const unsigned long DISPLAY_INTERVAL_MS = 200;
const float ARRIVAL_RADIUS_M = 15.0f;
const float HEADING_SMOOTH_ALPHA = 0.18f;  // lager = stabieler, trager
// Draai heading zodat "vooruit" = pijl omhoog (pas aan per montage, bv. 90/180)
const float HEADING_MOUNT_OFFSET_DEG = 0.0f;

// --- Waypoint / GPS state ---
bool haveTarget = false;
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

// --- IMU / heading ---
float headingDeg = 0.0f;          // 0..360, device forward vs magnetic north
bool haveHeading = false;

// Ruwe hard-iron offsets (pas aan na korte kalibratie / ronddraaien)
float magOffsetX = 0.0f;
float magOffsetY = 0.0f;
float magOffsetZ = 0.0f;

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
// Serial: waypoint ontvangen
// Protocol:  WP:<lat>,<lon>     bv. WP:51.053700,3.725000
// Optioneel: CLEAR              wis waypoint
// ---------------------------------------------------------------------------

void handleSerialLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line.equalsIgnoreCase("CLEAR")) {
    haveTarget = false;
    haveBearing = false;
    Serial.println("OK CLEAR");
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

  mx -= magOffsetX;
  my -= magOffsetY;
  mz -= magOffsetZ;

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

  // Horizontaal: zelfde assen-idee als Bijlage_A (atan2(my, mx)), plus tilt
  float rawHeading = wrap360(radToDeg(atan2(myH, mxH)) + HEADING_MOUNT_OFFSET_DEG);

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
    display.println("Wacht op WP...");
    display.println("Serial:");
    display.println("WP:lat,lon");
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

  showBootMessage("Navigator OK");
  delay(800);
  Serial.println("READY");
  Serial.println("Send WP:<lat>,<lon>");
}

void loop() {
  pollSerial();
  pollGPS();
  updateHeadingFromIMU();
  updateBearingFromGPS();
  updateDisplay();
}
