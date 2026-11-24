// ChocPilot – firmware. Cienka warstwa: skan 8 klawiszy, ekran, kilka ustawień.
// Logika akcji, gestów i profili działa w aplikacji na PC (protokół: docs/PROTOCOL.md).
#include <Arduino.h>
#include <string.h>

#include "boards/board.h"
#include "config.h"
#include "device_config.h"
#include "display_tft.h"
#include "fallback.h"
#include "hal/hal.h"
#include "matrix.h"
#include "protocol.h"
#include "protocol_codec.h"
#include "settings.h"
#include "time_util.h"
#include "wall_clock.h"

#include "controls.h"
#include "hid_codes.h"
#include "led_effects.h"
#include "leds.h"

using namespace chocpilot;

namespace {

DeviceConfig gConfig;
ConfigStore gStore;
Matrix gMatrix;
Display gDisplay;
Link gLink;
Fallback gFallback(gConfig.fallback);
Command gCommand;
WallClock gClock;  // czas z aplikacji (komenda time) – zegar na wygaszaczu LCD
IconStore gIcons;  // ikony klawiszy z aplikacji (komenda icon)

bool gOnline = false;
uint32_t gLastRx = 0;
bool gEverRx = false;

uint32_t gLastScanUs = 0;

bool gTestMode = false;
TestSnapshot gTest;
uint32_t gComboSince = 0;  // od kiedy trzymane K1+K4 (0 = nie)
bool gComboFired = false;

Controls gControls;
// Podświetlenie: gConfig.leds = zapisane ustawienia, gLedLive = stosowane teraz (może mieć kolor
// profilu wysłany z save:false – po rozłączeniu wraca do zapisanych).
LedSettings gLedLive;
uint32_t gLastLedMs = 0;
Rgb gLedFrame[board::kLedCount];
bool gLedFrameValid = false;
uint32_t gLedSentMs = 0;
uint32_t gKeyDownAt[kTotalKeys] = {0};
uint8_t gLedReact = 0;

void applySettings() {
  gDisplay.applySettings(gConfig.settings);
  gDisplay.setSaver(gConfig.saver.name);
}

void setTestMode(bool active) {
  if (gTestMode == active) return;
  gTestMode = active;
  if (active) {
    gTest.encoders[0] = 0;
    gTest.encoders[1] = 0;
  }
  gDisplay.setTestMode(active);
  gLink.sendTest(active);
}

void setOnline(bool online) {
  if (gOnline == online) return;
  gOnline = online;
  gFallback.setEnabled(!online);
  gDisplay.setOnline(online);
  if (!online) gLedLive = gConfig.leds;  // kolor profilu tylko przy działającej aplikacji
  gLink.sendLog(CHOCPILOT_F("info"), online ? CHOCPILOT_F("online") : CHOCPILOT_F("offline"));
}

void onUserActivity(uint32_t now) {
  gDisplay.activity(now);
}

void onKeyChange(uint8_t key, bool down) {
  const uint32_t now = millis();
  gLink.sendKey(key, down, now);
  gFallback.onKey(key, down);
  gTest.keys[key - 1] = down;
  if (down) {
    gKeyDownAt[key - 1] = now;
    gLedReact = static_cast<uint8_t>(gLedReact | (1u << (key - 1)));
  }
  onUserActivity(now);
}

// Pokrętła i suwak: zdarzenia zawsze do aplikacji; offline pokrętło 1 = głośność ± i wyciszenie.
void onEncoder(uint8_t index, int16_t delta) {
  const uint32_t now = millis();
  gLink.sendEncoder(index, delta, now);
  if (index == 1) {
    const uint16_t usage = delta > 0 ? kConsumerVolUp : kConsumerVolDown;
    for (int16_t i = delta > 0 ? delta : -delta; i > 0; --i) gFallback.tapMedia(usage);
  }
  gTest.encoders[index - 1] = static_cast<int16_t>(gTest.encoders[index - 1] + delta);
  onUserActivity(now);
}

void onEncoderKey(uint8_t index, bool down) {
  const uint32_t now = millis();
  gLink.sendEncoderKey(index, down, now);
  if (index == 1 && down) gFallback.tapMedia(kConsumerMute);
  gTest.encoderKeys[index - 1] = down;
  onUserActivity(now);
}

void onSlider(uint8_t value) {
  const uint32_t now = millis();
  gLink.sendSlider(value, now);
  gTest.slider = value;
  onUserActivity(now);
}

// Podświetlenie blatu – efekt z ustawień leds (led_effects.cpp), co 20 ms; do diod idzie tylko
// zmieniona klatka. Wygaszacz ekranu gasi też diody, tryb testu pokazuje kolejno R, G, B, biały.
void updateLeds(uint32_t now) {
  if (now - gLastLedMs < 20) return;
  gLastLedMs = now;
  LedFrame frame;
  frame.now = now;
  frame.online = gOnline;
  frame.sleeping = gDisplay.sleeping();
  frame.test = gTestMode;
  frame.reactMask = gLedReact;
  frame.keyDownAt = gKeyDownAt;
  frame.keyLed = board::kKeyLed;
  Rgb next[board::kLedCount];
  gLedReact = renderLeds(gLedLive, frame, next, board::kLedCount);
  // Ta sama klatka co ostatnio: bez wysyłania, ale co sekundę ponownie – zakłócenie linii
  // danych (np. ESD) nie zostaje na diodach na stałe.
  const bool same = gLedFrameValid && memcmp(next, gLedFrame, sizeof(next)) == 0;
  if (same && now - gLedSentMs < 1000) return;
  memcpy(gLedFrame, next, sizeof(next));
  gLedFrameValid = true;
  gLedSentMs = now;
  leds::show(gLedFrame, board::kLedCount);
}

void handleCommand(const Command& cmd, uint32_t now) {
  switch (cmd.type) {
    case CommandType::Hello:
      setOnline(true);
      gLink.sendHello(true);
      break;
    case CommandType::GetInfo:
      gLink.sendHello(gOnline);
      break;
    case CommandType::Ping:
      break;
    case CommandType::Display: {
      const DisplayCommand& d = cmd.display;
      if (d.mode == DisplayMode::Profile || d.mode == DisplayMode::Grid) {
        gConfig.display.mode = d.mode;
        memcpy(gConfig.display.title, d.title, sizeof(gConfig.display.title));
        memcpy(gConfig.display.labels, d.labels, sizeof(gConfig.display.labels));
        gStore.markDirty(now);
      }
      gDisplay.apply(d, now);
      break;
    }
    case CommandType::Flash:
      gDisplay.flash(cmd.flash.key, cmd.flash.text, cmd.flash.ms, now);
      break;
    case CommandType::Settings:
      cmd.settings.applyTo(gConfig.settings);
      if (cmd.settings.mask & SettingsPatch::kSaver) {
        memcpy(gConfig.saver.name, cmd.settings.saver, sizeof(gConfig.saver.name));
      }
      applySettings();
      gStore.markDirty(now);
      break;
    case CommandType::Icon:
      if (cmd.icon.clear) {
        gIcons.clear(cmd.icon.key);
        gDisplay.iconsChanged();
      } else if (gIcons.write(cmd.icon.key, cmd.icon.offset, cmd.icon.data, cmd.icon.len)) {
        gDisplay.iconsChanged();
      }
      break;
    case CommandType::Time:
      gClock.set(cmd.time.hour, cmd.time.minute, cmd.time.second, now);
      break;
    case CommandType::Leds:
      cmd.leds.applyTo(gLedLive);
      if (cmd.leds.save) {
        cmd.leds.applyTo(gConfig.leds);
        gStore.markDirty(now);
      }
      break;
    case CommandType::SetFallback:
      cmd.fallback.applyTo(gConfig.fallback);
      gStore.markDirty(now);
      break;
    case CommandType::Reboot:
      if (cmd.hasId) gLink.sendAck(cmd.id);
      hal::serialFlush();
      gStore.flush(gConfig);
      hal::reboot(cmd.flag);
      break;
    case CommandType::TestMode:
      setTestMode(cmd.flag);
      break;
    case CommandType::Debug:
      gLink.debug = cmd.flag;
      break;
    case CommandType::Unknown:
      break;
  }
}

void onLine(const char* line, size_t len) {
  const uint32_t now = millis();
  const ParseResult result = parseCommand(line, len, gCommand);
  switch (result.status) {
    case ParseStatus::BadJson:
      gLink.sendError(false, 0, result.error);
      return;
    case ParseStatus::Invalid:
      gLastRx = now;
      gEverRx = true;
      gLink.sendError(gCommand.hasId, gCommand.id, result.error);
      return;
    case ParseStatus::Ignored:
      gLastRx = now;
      gEverRx = true;
      return;
    case ParseStatus::Ok:
      break;
  }
  gLastRx = now;
  gEverRx = true;
  handleCommand(gCommand, now);
  if (gCommand.hasId && gCommand.type != CommandType::Reboot) gLink.sendAck(gCommand.id);
}

void updateHeartbeat(uint32_t now) {
  // gLastRx bywa o 1 ms późniejszy niż `now` z początku obiegu – stąd elapsed() ze znakiem.
  const bool alive = gEverRx && !elapsed(now, gLastRx, kHeartbeatTimeoutMs);
  setOnline(alive);
}

// K1+K4 (skrajne klawisze górnego rzędu) trzymane 3 s: zaraz po starcie włącza tryb testu,
// w trybie testu – wyłącza.
void updateTestCombo(uint32_t now) {
  const bool combo = gMatrix.pressed(1) && gMatrix.pressed(kCols);
  if (!combo) {
    gComboSince = 0;
    gComboFired = false;
    return;
  }
  if (gComboSince == 0) gComboSince = now;
  const bool eligible = gTestMode || gComboSince <= kTestComboBootWindowMs;
  if (eligible && !gComboFired && now - gComboSince >= kTestComboHoldMs) {
    gComboFired = true;
    setTestMode(!gTestMode);
  }
}

}  // namespace

void setup() {
  const bool loaded = gStore.load(gConfig);
  // Ekran przed USB: inicjalizacja LCD trwa ok. 0,4 s, a host zaczyna wyliczanie zaraz po
  // włączeniu USB.
  gDisplay.begin(gConfig.settings);
  gDisplay.restore(gConfig.display);
  gDisplay.setClock(&gClock);
  gDisplay.setIcons(&gIcons);
  gLink.iconSize = kIconSize;
  gLink.savers = saverNames();
  gLink.saverCount = saverCount();

  hal::usbBegin();
  gLink.begin();

  gMatrix.begin();
  gControls.begin();
  leds::begin();
  gLedLive = gConfig.leds;
  applySettings();
  gFallback.setEnabled(true);

  gLink.sendHello(false);
  gLink.sendLog(CHOCPILOT_F("info"),
                loaded ? CHOCPILOT_F("config loaded") : CHOCPILOT_F("default config"));
}

void loop() {
  hal::poll();
  const uint32_t now = millis();

  const uint32_t nowUs = micros();
  if (nowUs - gLastScanUs >= kScanIntervalUs) {
    gLastScanUs = nowUs;
    gMatrix.scan(now, gConfig.settings.debounceMs, onKeyChange);
    gControls.update(now, gConfig.settings.debounceMs, onEncoder, onEncoderKey, onSlider);
    updateTestCombo(now);
  }

  gLink.poll(onLine);
  updateHeartbeat(now);
  gFallback.update();

  gDisplay.setTestSnapshot(gTest);
  gDisplay.update(now);
  updateLeds(now);

  if (gStore.update(gConfig, now)) {
    gLink.sendLog(CHOCPILOT_F("info"), CHOCPILOT_F("config saved"));
  }
}
