#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <driver/i2s.h>   // legacy I2S driver
#include <math.h>
#include <time.h>         // NTP time
#include "secrets.h"      // WIFI_SSID / WIFI_PASSWORD

// ── Custom font: FreeMonoBold9pt7b gives a clean, larger look on 128x64 OLEDs.
// Include only one — the compiler will use it instead of the built-in 6x8 font.
#include <Fonts/FreeSansBold9pt7b.h>   // clean sans-serif, fits ~10 chars per line
#include <Fonts/FreeMono9pt7b.h>        // monospace — used for time/temp display

const char* ssid     = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// ── NTP ───────────────────────────────────────────────────────────────────────
const char* NTP_SERVER = "pool.ntp.org";
const long  GMT_OFFSET = 19800;   // IST = UTC+5:30 = 5.5 * 3600
const int   DST_OFFSET = 0;

WebServer server(80);

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

const int LED_PIN   = 2;
const int RELAY_PIN = 5;    // Relay module IN pin  (GPIO 5)
const int PUMP_PIN  = 18;   // Pump relay IN pin    (GPIO 18)
// Most relay modules are ACTIVE LOW: HIGH = OFF, LOW = ON.
// Set RELAY_ACTIVE_LOW true if yours follows that convention.
#define RELAY_ACTIVE_LOW true

// Helper: write to a relay pin respecting active-low wiring
void relayWrite(int pin, bool on) {
  digitalWrite(pin, RELAY_ACTIVE_LOW ? !on : on);
}

// ── Audio (I2S) ───────────────────────────────────────────────────────────────
#define MIC_BCLK   26
#define MIC_WS     25
#define MIC_SD     32
#define MIC_LR     17
#define SPK_BCLK   14
#define SPK_LRC    27
#define SPK_DIN    33
#define AUDIO_RATE  16000
#define MIC_SHIFT   11

// ── OLED state ────────────────────────────────────────────────────────────────
String oledText  = "";          // "" = show idle clock+temp screen
int    scrollPos = 0;
unsigned long lastScroll  = 0;
unsigned long msgClearAt  = 0;  // millis() when to return to idle; 0 = never

// ── Simulated temperature (swap with real sensor read when you have one) ──────
// When you connect a DHT11/22: replace this function body with sensor.readTemperature()
float readTemperature() {
  // Sine-wave drift ±2 °C around 28 °C — looks alive on the dashboard.
  float t = millis() / 60000.0f;
  return 28.0f + 2.0f * sinf(t);
}

// ── Helpers: get current time string ─────────────────────────────────────────
String getTimeStr() {
  struct tm ti;
  if (!getLocalTime(&ti)) return "--:--";
  char buf[8];
  strftime(buf, sizeof(buf), "%H:%M", &ti);
  return String(buf);
}

String getDateStr() {
  struct tm ti;
  if (!getLocalTime(&ti)) return "";
  char buf[12];
  strftime(buf, sizeof(buf), "%d %b %Y", &ti);
  return String(buf);
}

// ── OLED rendering ────────────────────────────────────────────────────────────
// Idle screen: large time + temp (monospace font, clear layout)
void drawIdleScreen() {
  display.clearDisplay();

  // Time — large, top half
  display.setFont(&FreeMono9pt7b);
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  String t = getTimeStr();
  display.setCursor(0, 26);
  display.print(t);

  // Date — small, below time
  display.setFont(&FreeSansBold9pt7b);
  display.setTextSize(1);
  display.setCursor(0, 44);
  display.print(getDateStr());

  // Temperature — bottom right
  char tempBuf[10];
  snprintf(tempBuf, sizeof(tempBuf), "%.1fC", readTemperature());
  // Right-align: each char ≈ 10px wide in FreeSansBold9pt7b size 1
  int16_t tx = SCREEN_WIDTH - (strlen(tempBuf) * 10);
  display.setCursor(max((int16_t)70, tx), 44);
  display.print(tempBuf);

  display.display();
}

// AI / message screen: scrolling text in clean sans-serif font
void updateOLED() {
  // If a timed message has expired, return to idle
  if (msgClearAt > 0 && millis() > msgClearAt) {
    oledText  = "";
    msgClearAt = 0;
    drawIdleScreen();
    return;
  }

  if (oledText == "") {
    // Refresh idle screen every second
    static unsigned long lastIdle = 0;
    if (millis() - lastIdle > 1000) {
      lastIdle = millis();
      drawIdleScreen();
    }
    return;
  }

  // Scroll text: advance one character every 280 ms
  if (millis() - lastScroll < 280) return;
  lastScroll = millis();

  display.clearDisplay();
  display.setFont(&FreeSansBold9pt7b);   // clean sans-serif for messages
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);

  // FreeSansBold9pt7b at size 1: ~10 px per char, 3 lines visible (y=14, 30, 46)
  // Show a 12-char window (fits one line nicely)
  const int WIN = 12;
  String part = oledText.substring(
    scrollPos,
    min(scrollPos + WIN, (int)oledText.length())
  );

  display.setCursor(0, 18);
  display.print(part);
  display.display();

  if (scrollPos + WIN < (int)oledText.length()) {
    scrollPos++;
  } else {
    static int holdCount = 0;
    if (++holdCount >= 8) {
      holdCount = 0;
      scrollPos = 0;
    }
  }
}

// ── HTTP handlers ─────────────────────────────────────────────────────────────
void handleLedOn()  { Serial.println("LED ON");  digitalWrite(LED_PIN, HIGH); server.send(200,"text/plain","LED ON");  }
void handleLedOff() { Serial.println("LED OFF"); digitalWrite(LED_PIN, LOW);  server.send(200,"text/plain","LED OFF"); }

void handleRelayOn()  { Serial.println("RELAY ON");  relayWrite(RELAY_PIN, true);  server.send(200,"text/plain","RELAY ON");  }
void handleRelayOff() { Serial.println("RELAY OFF"); relayWrite(RELAY_PIN, false); server.send(200,"text/plain","RELAY OFF"); }

void handlePumpOn()  { Serial.println("PUMP ON");  relayWrite(PUMP_PIN, true);  server.send(200,"text/plain","PUMP ON");  }
void handlePumpOff() { Serial.println("PUMP OFF"); relayWrite(PUMP_PIN, false); server.send(200,"text/plain","PUMP OFF"); }

void handleDisplay() {
  oledText  = server.arg("text");
  scrollPos = 0;
  lastScroll = millis();
  // Auto-clear after 30 s so the clock comes back
  msgClearAt = millis() + 30000;
  Serial.println("DISPLAY: " + oledText);
  server.send(200, "text/plain", "TEXT DISPLAYED");
}

// GET /status — returns JSON with time, date, temperature, and device states
void handleStatus() {
  float temp = readTemperature();
  String ledState   = digitalRead(LED_PIN) ? "on" : "off";
  // ACTIVE_LOW: pin LOW = on
  String relayState = (RELAY_ACTIVE_LOW ? !digitalRead(RELAY_PIN) : digitalRead(RELAY_PIN)) ? "on" : "off";
  String pumpState  = (RELAY_ACTIVE_LOW ? !digitalRead(PUMP_PIN)  : digitalRead(PUMP_PIN))  ? "on" : "off";

  String json = "{";
  json += "\"time\":\""   + getTimeStr()  + "\",";
  json += "\"date\":\""   + getDateStr()  + "\",";
  json += "\"temp_c\":"   + String(temp, 1)                        + ",";
  json += "\"temp_f\":"   + String(temp * 9.0f / 5.0f + 32.0f, 1) + ",";
  json += "\"led\":\""    + ledState   + "\",";
  json += "\"relay\":\""  + relayState + "\",";
  json += "\"pump\":\""   + pumpState  + "\"";
  json += "}";
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", json);
}

// ── I2S ──────────────────────────────────────────────────────────────────────
void setupI2SMic() {
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = AUDIO_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4, .dma_buf_len = 256,
    .use_apll = false, .tx_desc_auto_clear = false, .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num = MIC_BCLK, .ws_io_num = MIC_WS,
    .data_out_num = I2S_PIN_NO_CHANGE, .data_in_num = MIC_SD
  };
  i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pins);
}

void setupI2SSpeaker() {
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = AUDIO_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8, .dma_buf_len = 256,
    .use_apll = false, .tx_desc_auto_clear = true, .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num = SPK_BCLK, .ws_io_num = SPK_LRC,
    .data_out_num = SPK_DIN, .data_in_num = I2S_PIN_NO_CHANGE
  };
  i2s_driver_install(I2S_NUM_1, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_1, &pins);
  i2s_zero_dma_buffer(I2S_NUM_1);
}

void writeWavHeader(uint8_t* h, uint32_t dataBytes, uint32_t sampleRate) {
  uint32_t byteRate  = sampleRate * 2;
  uint32_t chunkSize = 36 + dataBytes;
  memcpy(h, "RIFF", 4);
  h[4]=chunkSize; h[5]=chunkSize>>8; h[6]=chunkSize>>16; h[7]=chunkSize>>24;
  memcpy(h+8, "WAVEfmt ", 8);
  h[16]=16; h[17]=0; h[18]=0; h[19]=0;
  h[20]=1; h[21]=0; h[22]=1; h[23]=0;
  h[24]=sampleRate; h[25]=sampleRate>>8; h[26]=sampleRate>>16; h[27]=sampleRate>>24;
  h[28]=byteRate; h[29]=byteRate>>8; h[30]=byteRate>>16; h[31]=byteRate>>24;
  h[32]=2; h[33]=0; h[34]=16; h[35]=0;
  memcpy(h+36, "data", 4);
  h[40]=dataBytes; h[41]=dataBytes>>8; h[42]=dataBytes>>16; h[43]=dataBytes>>24;
}

void handleRecord() {
  int seconds = server.hasArg("seconds") ? server.arg("seconds").toInt() : 5;
  if (seconds < 1) seconds = 1;
  if (seconds > 10) seconds = 10;
  const uint32_t numSamples = (uint32_t)AUDIO_RATE * seconds;
  const uint32_t dataBytes  = numSamples * 2;
  uint8_t header[44];
  writeWavHeader(header, dataBytes, AUDIO_RATE);
  server.setContentLength(44 + dataBytes);
  server.send(200, "audio/wav", "");
  server.sendContent((const char*)header, 44);
  const int CHUNK = 256;
  int32_t raw[CHUNK]; int16_t out[CHUNK];
  uint32_t sent = 0;
  while (sent < numSamples) {
    size_t bytesRead = 0;
    i2s_read(I2S_NUM_0, raw, sizeof(raw), &bytesRead, portMAX_DELAY);
    int got = bytesRead / sizeof(int32_t), n = 0;
    for (int i = 0; i < got && sent < numSamples; i++, sent++)
      out[n++] = (int16_t)(raw[i] >> MIC_SHIFT);
    server.sendContent((const char*)out, n * sizeof(int16_t));
  }
}

void handlePlayUpload() {
  HTTPUpload& up = server.upload();
  if (up.status == UPLOAD_FILE_WRITE) {
    size_t w = 0;
    i2s_write(I2S_NUM_1, up.buf, up.currentSize, &w, portMAX_DELAY);
  } else if (up.status == UPLOAD_FILE_END) {
    i2s_zero_dma_buffer(I2S_NUM_1);
  }
}

void handlePlayDone() { server.send(200, "text/plain", "PLAYED"); }

void playTone(int freq, int ms) {
  const int total = (AUDIO_RATE * ms) / 1000;
  int16_t buf[256];
  for (int i = 0; i < total; ) {
    int n = 0;
    while (n < 256 && i < total) {
      float t = (float)i / AUDIO_RATE;
      buf[n++] = (int16_t)(8000.0f * sinf(2.0f * 3.14159265f * freq * t));
      i++;
    }
    size_t w;
    i2s_write(I2S_NUM_1, buf, n * sizeof(int16_t), &w, portMAX_DELAY);
  }
  i2s_zero_dma_buffer(I2S_NUM_1);
}

void handleTone() {
  playTone(440, 500);
  server.send(200, "text/plain", "TONE");
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN,   OUTPUT); digitalWrite(LED_PIN, LOW);
  pinMode(RELAY_PIN, OUTPUT); relayWrite(RELAY_PIN, false);  // relay off on boot
  pinMode(PUMP_PIN,  OUTPUT); relayWrite(PUMP_PIN,  false);  // pump  off on boot
  Wire.begin(4, 15);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed! Check wiring.");
  }

  // Boot screen
  display.clearDisplay();
  display.setFont(&FreeSansBold9pt7b);
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 18);
  display.println("Connecting...");
  display.display();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nWiFi: " + WiFi.localIP().toString());

  // Sync NTP time (IST)
  configTime(GMT_OFFSET, DST_OFFSET, NTP_SERVER);
  Serial.println("NTP synced.");

  pinMode(MIC_LR, OUTPUT);
  digitalWrite(MIC_LR, LOW);
  setupI2SMic();
  setupI2SSpeaker();
  playTone(440, 400);   // boot beep

  server.on("/led/on",    handleLedOn);
  server.on("/led/off",   handleLedOff);
  server.on("/relay/on",  handleRelayOn);
  server.on("/relay/off", handleRelayOff);
  server.on("/pump/on",   handlePumpOn);
  server.on("/pump/off",  handlePumpOff);
  server.on("/display",   handleDisplay);
  server.on("/status",    handleStatus);
  server.on("/record",    handleRecord);
  server.on("/play",  HTTP_POST, handlePlayDone, handlePlayUpload);
  server.on("/tone",      handleTone);
  server.begin();

  Serial.println("Server started.");
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
  server.handleClient();
  updateOLED();

  static unsigned long lastAlive = 0;
  if (millis() - lastAlive > 5000) {
    Serial.println("ALIVE  " + getTimeStr() + "  " + String(readTemperature(), 1) + "C");
    lastAlive = millis();
  }
}
