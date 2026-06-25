#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ⚠️  Move these to a secrets file or use NVS before sharing your code.
const char* ssid     = "A103";
const char* password = "zilaara823001";

WebServer server(80);

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &Wire,
  -1
);

const int LED_PIN = 2;

String oledText = "";
int scrollPos = 0;
unsigned long lastScroll = 0;

void handleLedOn() {

  Serial.println("LED ON REQUEST");

  digitalWrite(LED_PIN, HIGH);

  server.send(200, "text/plain", "LED ON");
}

void handleLedOff() {

  Serial.println("LED OFF REQUEST");

  digitalWrite(LED_PIN, LOW);

  server.send(200, "text/plain", "LED OFF");
}

void handleDisplay() {

  oledText = server.arg("text");

  Serial.println("DISPLAY REQUEST:");
  Serial.println(oledText);

  scrollPos = 0;
  lastScroll = millis();  // reset timer from now, not from 0

  server.send(200, "text/plain", "TEXT DISPLAYED");
}

void updateOLED() {

  if (oledText == "")
    return;

  // Scroll every 300 ms — one character at a time for smooth reading
  if (millis() - lastScroll < 300)
    return;

  lastScroll = millis();

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  // Show a 20-char window starting at scrollPos
  const int WIN = 20;
  String part = oledText.substring(
    scrollPos,
    min(scrollPos + WIN, (int)oledText.length())
  );

  display.setCursor(0, 0);
  display.println(part);
  display.display();

  // Advance one character; wrap back to start after a brief pause at end
  if (scrollPos + WIN < (int)oledText.length()) {
    scrollPos++;
  } else {
    // Hold at end for ~2 s (2000/300 ≈ 7 more cycles) then restart
    static int holdCount = 0;
    if (++holdCount >= 7) {
      holdCount  = 0;
      scrollPos  = 0;
    }
  }
}

void setup() {

  Serial.begin(115200);

  pinMode(LED_PIN, OUTPUT);

  Wire.begin(4, 15);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed! Check wiring.");
    // Continue anyway — LED/display routes still work via HTTP
  }

  display.clearDisplay();

  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("BOOT OK");
  display.display();

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi Connected!");
  Serial.println(WiFi.localIP());

  server.on("/led/on", handleLedOn);
  server.on("/led/off", handleLedOff);
  server.on("/display", handleDisplay);

  server.begin();

  Serial.println("Server Started");
}

void loop() {

  server.handleClient();

  updateOLED();

  static unsigned long last = 0;

  if (millis() - last > 5000) {
    Serial.println("ALIVE");
    last = millis();
  }
}
