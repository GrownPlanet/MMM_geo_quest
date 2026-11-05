# Arduino navigator

Toont op de OLED een pijl naar het volgende tussenpunt.

1. Ontvangt een waypoint via Serial: `WP:<lat>,<lon>`
2. Leest de eigen GPS-positie
3. Berekent elke 3 s de richting naar het doel
4. Tussendoor volgt de pijl de IMU-heading (tilt-compensatie + smoothing)

**Hardware:** GPS (UART 7/8), BMI270/BMM150, SSD1306 OLED (0x3C)  
**Serial:** 115200 baud — `CLEAR` wist het waypoint
