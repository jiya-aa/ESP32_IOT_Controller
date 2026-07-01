#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <driver/i2s.h>   // legacy I2S driver (works on core 2.x & 3.x; do NOT add
                          // an audio library that uses the new driver — they conflict)
#include <math.h>         // sinf() for the diagnostic test tone
#include "secrets.h"   // WIFI_SSID / WIFI_PASSWORD — copy secrets.h.example to secrets.h


const char* ssid     = WIFI_SSID;
const char* password = WIFI_PASSWORD;

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

// ── Audio (I2S) ──────────────────────────────────────────────────────────────
// INMP441 microphone on I2S_NUM_0 (RX). MAX98357A amplifier on I2S_NUM_1 (TX).
// Pins avoid LED (2) and the OLED I2C bus (SDA 4 / SCL 15).
#define MIC_BCLK   26      // INMP441 SCK
#define MIC_WS     25      // INMP441 WS
#define MIC_SD     32      // INMP441 SD  (data out of mic → ESP32)
#define MIC_LR     17      // INMP441 L/R, wired to TX2 — driven LOW = left channel

#define SPK_BCLK   14      // MAX98357A BCLK
#define SPK_LRC    27      // MAX98357A LRC
#define SPK_DIN    33      // MAX98357A DIN

#define AUDIO_RATE  16000  // 16 kHz, 16-bit mono — matches Whisper / the PC side
#define MIC_SHIFT   11     // INMP441 32-bit → 16-bit gain shift; raise = quieter

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

// ── I2S setup ────────────────────────────────────────────────────────────────
void setupI2SMic() {
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = AUDIO_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,   // INMP441 needs 32-bit slots
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 256,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num = MIC_BCLK,
    .ws_io_num = MIC_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = MIC_SD
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
    .dma_buf_count = 8,
    .dma_buf_len = 256,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num = SPK_BCLK,
    .ws_io_num = SPK_LRC,
    .data_out_num = SPK_DIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };
  i2s_driver_install(I2S_NUM_1, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_1, &pins);
  i2s_zero_dma_buffer(I2S_NUM_1);
}

// Fill a 44-byte canonical PCM WAV header for 16-bit mono audio.
void writeWavHeader(uint8_t* h, uint32_t dataBytes, uint32_t sampleRate) {
  uint32_t byteRate   = sampleRate * 2;   // mono, 16-bit
  uint32_t chunkSize  = 36 + dataBytes;
  memcpy(h, "RIFF", 4);
  h[4]=chunkSize; h[5]=chunkSize>>8; h[6]=chunkSize>>16; h[7]=chunkSize>>24;
  memcpy(h+8, "WAVEfmt ", 8);
  h[16]=16; h[17]=0; h[18]=0; h[19]=0;     // fmt chunk size = 16
  h[20]=1;  h[21]=0;                        // PCM
  h[22]=1;  h[23]=0;                        // 1 channel
  h[24]=sampleRate; h[25]=sampleRate>>8; h[26]=sampleRate>>16; h[27]=sampleRate>>24;
  h[28]=byteRate; h[29]=byteRate>>8; h[30]=byteRate>>16; h[31]=byteRate>>24;
  h[32]=2; h[33]=0;                         // block align
  h[34]=16; h[35]=0;                        // bits per sample
  memcpy(h+36, "data", 4);
  h[40]=dataBytes; h[41]=dataBytes>>8; h[42]=dataBytes>>16; h[43]=dataBytes>>24;
}

// GET /record?seconds=N — stream a 16 kHz/16-bit/mono WAV captured from the mic.
void handleRecord() {
  int seconds = server.hasArg("seconds") ? server.arg("seconds").toInt() : 5;
  if (seconds < 1)  seconds = 1;
  if (seconds > 10) seconds = 10;

  const uint32_t numSamples = (uint32_t)AUDIO_RATE * seconds;
  const uint32_t dataBytes  = numSamples * 2;

  Serial.printf("RECORD REQUEST: %d s (%u bytes)\n", seconds, dataBytes);

  uint8_t header[44];
  writeWavHeader(header, dataBytes, AUDIO_RATE);

  server.setContentLength(44 + dataBytes);
  server.send(200, "audio/wav", "");
  server.sendContent((const char*)header, 44);

  const int CHUNK = 256;          // samples per I2S read
  int32_t raw[CHUNK];
  int16_t out[CHUNK];
  uint32_t sent = 0;
  while (sent < numSamples) {
    size_t bytesRead = 0;
    i2s_read(I2S_NUM_0, raw, sizeof(raw), &bytesRead, portMAX_DELAY);
    int got = bytesRead / sizeof(int32_t);
    int n = 0;
    for (int i = 0; i < got && sent < numSamples; i++, sent++) {
      out[n++] = (int16_t)(raw[i] >> MIC_SHIFT);   // 32-bit mic sample → 16-bit
    }
    server.sendContent((const char*)out, n * sizeof(int16_t));
  }
  Serial.println("RECORD DONE");
}

// POST /play — body is raw 16 kHz/16-bit/mono PCM (multipart file field).
// Streamed straight to I2S; the blocking write paces the upload to real time.
void handlePlayUpload() {
  HTTPUpload& up = server.upload();
  if (up.status == UPLOAD_FILE_WRITE) {
    size_t written = 0;
    i2s_write(I2S_NUM_1, up.buf, up.currentSize, &written, portMAX_DELAY);
  } else if (up.status == UPLOAD_FILE_END) {
    i2s_zero_dma_buffer(I2S_NUM_1);   // silence the line after playback
    Serial.printf("PLAY DONE: %u bytes\n", up.totalSize);
  }
}

void handlePlayDone() {
  server.send(200, "text/plain", "PLAYED");
}

// Diagnostic: synthesise a sine wave on the ESP32 and play it through the amp.
// If THIS sounds clean but /play is noise, the problem is the PCM transport, not
// the wiring/I2S/amp. If this is also noise, check BCLK/LRC wiring + I2S config.
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
  Serial.println("TONE REQUEST");
  playTone(440, 500);
  server.send(200, "text/plain", "TONE");
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

  // INMP441 L/R is wired to TX2 (GPIO 17); hold it LOW so the mic uses the
  // left channel (matches the I2S ONLY_LEFT config). Tie to GND instead if free.
  pinMode(MIC_LR, OUTPUT);
  digitalWrite(MIC_LR, LOW);

  setupI2SMic();
  setupI2SSpeaker();
  Serial.println("I2S ready");

  // Boot self-test: a clean 440 Hz beep means wiring + I2S + amp are good.
  playTone(440, 400);

  server.on("/led/on", handleLedOn);
  server.on("/led/off", handleLedOff);
  server.on("/display", handleDisplay);
  server.on("/record", handleRecord);
  server.on("/play", HTTP_POST, handlePlayDone, handlePlayUpload);
  server.on("/tone", handleTone);

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
