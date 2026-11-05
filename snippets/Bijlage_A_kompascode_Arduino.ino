
#include <Wire.h>
#include <Arduino_BMI270_BMM150.h>
#include <LiquidCrystal_I2C.h>
#include <math.h>

// LCD-instellingen
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Magnetometerwaarden
float mag_x, mag_y, mag_z;
float heading;
const char* direction;

// Acht pijlsymbolen voor de kompasrichtingen
byte arrows[8][8] = {
  {B00100, B01110, B10101, B00100, B00100, B00100, B00100, B00000}, // Noord
  {B00000, B00001, B00011, B00101, B01001, B10000, B00000, B00000}, // Noordoost
  {B00000, B00100, B00010, B11111, B00010, B00100, B00000, B00000}, // Oost
  {B00000, B10000, B01000, B00100, B00110, B00011, B00001, B00000}, // Zuidoost
  {B00100, B00100, B00100, B00100, B10101, B01110, B00100, B00000}, // Zuid
  {B00000, B00001, B00011, B00110, B00100, B01000, B10000, B00000}, // Zuidwest
  {B00000, B00100, B01000, B11111, B01000, B00100, B00000, B00000}, // West
  {B00000, B10000, B11000, B10100, B10010, B00001, B00000, B00000}  // Noordwest
};

void setup() {
  Serial.begin(9600);

  // Start het LCD
  lcd.init();
  lcd.backlight();

  byte testArrow[8] = {
  B00100,
  B01110,
  B11111,
  B00100,
  B00100,
  B00100,
  B00100,
  B00000
  };

  lcd.createChar(0, testArrow);
  lcd.setCursor(15, 0);
  lcd.write((uint8_t)0);
  delay(2000);
  lcd.clear();

  // Maak de acht eigen LCD-tekens aan
  for (int i = 0; i < 8; i++) {
    lcd.createChar(i, arrows[i]);
  }

  // Start de magnetometer
  if (!IMU.begin()) {
    lcd.setCursor(0, 0);
    lcd.print("Sensor error");
    while (true) {
      delay(100);
    }
  }

  lcd.setCursor(0, 0);
  lcd.print("Compass ready");
  delay(1000);
  lcd.clear();
}

void loop() {
  if (IMU.magneticFieldAvailable()) {
    IMU.readMagneticField(mag_x, mag_y, mag_z);

    // Bereken de hoek in graden
    heading = atan2(mag_y, mag_x) * 180.0 / PI;

    // Zet de hoek om naar 0-360 graden
    if (heading < 0) {
      heading += 360.0;
    }

    // Bepaal de windrichting
    if (heading >= 315.0 || heading < 45.0) {
      direction = "N";
    }
    else if (heading < 135.0) {
      direction = "E";
    }
    else if (heading < 225.0) {
      direction = "S";
    }
    else {
      direction = "W";
    }

    // Bepaal welke van de acht pijlen wordt getoond
    int arrowIndex = ((int)(heading + 22.5) / 45) % 8;

    // Toon de hoek op de eerste regel
    lcd.setCursor(0, 0);
    lcd.print("Heading:        ");
    lcd.setCursor(9, 0);
    lcd.print(heading, 1);
    lcd.write((uint8_t)223);

    // Toon de windrichting en de pijl
    lcd.setCursor(0, 1);
    lcd.print("Direction: ");
    lcd.print(direction);
    lcd.print(" ");

    lcd.setCursor(15, 1);
    lcd.write((uint8_t)arrowIndex);

    // Toon de gegevens in de Serial Monitor
    Serial.print("Heading: ");
    Serial.print(heading, 1);
    Serial.print(" degrees | Direction: ");
    Serial.print(direction);
    Serial.print(" | Arrow index: ");
    Serial.println(arrowIndex);
  }

  delay(200);
}
