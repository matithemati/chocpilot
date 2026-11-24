// Testy parsera protokołu, budowania wiadomości, kodów HID i zapisu konfiguracji.
#include <stddef.h>
#include <string.h>
#include <unity.h>

#include "debouncer.h"
#include "device_config.h"
#include "hid_codes.h"
#include "led_effects.h"
#include "protocol_codec.h"
#include "time_util.h"
#include "wall_clock.h"

using namespace chocpilot;

namespace {

Command cmd;

ParseResult parse(const char* line) { return parseCommand(line, strlen(line), cmd); }

}  // namespace

void setUp() {}
void tearDown() {}

void test_invalid_json() {
  ParseResult r = parse("{not json");
  TEST_ASSERT_EQUAL(ParseStatus::BadJson, r.status);
  TEST_ASSERT_NOT_NULL(r.error);
  r = parse("[1,2]");
  TEST_ASSERT_EQUAL(ParseStatus::BadJson, r.status);
  r = parse("{\"id\":1}");
  TEST_ASSERT_EQUAL(ParseStatus::BadJson, r.status);
}

void test_unknown_type_is_ignored() {
  ParseResult r = parse("{\"type\":\"future_thing\",\"id\":5,\"x\":1}");
  TEST_ASSERT_EQUAL(ParseStatus::Ignored, r.status);
}

void test_ping_with_id_and_unknown_fields() {
  ParseResult r = parse("{\"type\":\"ping\",\"id\":42,\"extra\":{\"a\":[1,2]}}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL(CommandType::Ping, cmd.type);
  TEST_ASSERT_TRUE(cmd.hasId);
  TEST_ASSERT_EQUAL_INT32(42, cmd.id);
}

void test_hello_without_id() {
  ParseResult r = parse("{\"type\":\"hello\",\"app\":\"1.0.0\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL(CommandType::Hello, cmd.type);
  TEST_ASSERT_FALSE(cmd.hasId);
}

void test_display_grid() {
  ParseResult r = parse(
      "{\"type\":\"display\",\"mode\":\"grid\",\"title\":\"Domyslny\","
      "\"labels\":[\"Calc\",\"Notatnik 1234\",null,\"WWW\"]}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL(DisplayMode::Grid, cmd.display.mode);
  TEST_ASSERT_EQUAL_STRING("Domyslny", cmd.display.title);
  TEST_ASSERT_EQUAL_STRING("Calc", cmd.display.labels[0]);
  TEST_ASSERT_EQUAL_STRING("Notatnik 1", cmd.display.labels[1]);  // obcięte do 10 znaków
  TEST_ASSERT_EQUAL_STRING("", cmd.display.labels[2]);
  TEST_ASSERT_EQUAL_STRING("WWW", cmd.display.labels[3]);
  TEST_ASSERT_EQUAL_STRING("", cmd.display.labels[7]);
  // Więcej etykiet niż klawiszy (8) → błąd.
  r = parse("{\"type\":\"display\",\"mode\":\"grid\",\"labels\":[\"1\",\"2\",\"3\",\"4\",\"5\",\"6\","
            "\"7\",\"8\",\"9\"]}");
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, r.status);
}

void test_display_utf8_truncation() {
  // Wielobajtowe znaki: bufor etykiety (12 B) kończy się przed 10. znakiem – obcięcie bez
  // łamania sekwencji.
  ParseResult r = parse(
      "{\"type\":\"display\",\"mode\":\"grid\",\"labels\":[\"\xC5\x82\xC4\x85\xC5\x82\xC4\x85"
      "abcdef\"]}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL_STRING("\xC5\x82\xC4\x85\xC5\x82\xC4\x85" "abc", cmd.display.labels[0]);
}

void test_display_bar_and_text() {
  ParseResult r = parse("{\"type\":\"display\",\"mode\":\"bar\",\"title\":\"Vol\",\"value\":150,\"ms\":1500}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL(DisplayMode::Bar, cmd.display.mode);
  TEST_ASSERT_EQUAL_UINT8(100, cmd.display.value);
  TEST_ASSERT_EQUAL_UINT32(1500, cmd.display.ms);

  r = parse("{\"type\":\"display\",\"mode\":\"text\",\"line1\":\"A\",\"line2\":\"B\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL(DisplayMode::Text, cmd.display.mode);
  TEST_ASSERT_EQUAL_STRING("A", cmd.display.line1);
  TEST_ASSERT_EQUAL_UINT32(0, cmd.display.ms);
}

void test_display_errors() {
  ParseResult r = parse("{\"type\":\"display\",\"id\":3,\"mode\":\"weird\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, r.status);
  TEST_ASSERT_TRUE(cmd.hasId);
  TEST_ASSERT_EQUAL_INT32(3, cmd.id);
  r = parse("{\"type\":\"display\",\"mode\":\"grid\",\"labels\":\"x\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, r.status);
  r = parse("{\"type\":\"display\",\"mode\":\"text\",\"line1\":5}");
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, r.status);
}

void test_flash() {
  ParseResult r = parse("{\"type\":\"flash\",\"key\":3,\"text\":\"Spotify\",\"ms\":1200}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL_UINT8(3, cmd.flash.key);
  TEST_ASSERT_EQUAL_STRING("Spotify", cmd.flash.text);
  TEST_ASSERT_EQUAL_UINT32(1200, cmd.flash.ms);
  r = parse("{\"type\":\"flash\",\"key\":9,\"text\":\"x\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, r.status);
}

void test_settings_partial() {
  ParseResult r = parse("{\"type\":\"settings\",\"id\":1,\"brightness\":200,\"flip\":true}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  Settings s;
  cmd.settings.applyTo(s);
  TEST_ASSERT_EQUAL_UINT8(200, s.brightness);
  TEST_ASSERT_TRUE(s.flip);
  TEST_ASSERT_EQUAL_UINT8(8, s.debounceMs);  // bez zmian
}

void test_settings_validation() {
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"settings\",\"brightness\":300}").status);
  // Ustawienia pokrętła ze starszych aplikacji – nieznane pola są ignorowane.
  TEST_ASSERT_EQUAL(ParseStatus::Ok, parse("{\"type\":\"settings\",\"enc_pulses\":0}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"settings\",\"flip\":1}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"settings\",\"debounce_ms\":\"8\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Ok, parse("{\"type\":\"settings\",\"screensaver_s\":0}").status);
}

void test_fallback_single() {
  ParseResult r = parse("{\"type\":\"set_fallback\",\"key\":1,\"mods\":[\"ctrl\",\"shift\"],\"code\":\"c\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL_UINT8(1, cmd.fallback.count);
  TEST_ASSERT_EQUAL_UINT8(0, cmd.fallback.slots[0]);
  TEST_ASSERT_EQUAL_UINT8(kModLCtrl | kModLShift, cmd.fallback.bindings[0].mods);
  TEST_ASSERT_EQUAL_UINT8(0x06, cmd.fallback.bindings[0].code);
}

void test_fallback_list_and_replace() {
  ParseResult r = parse(
      "{\"type\":\"set_fallback\",\"replace\":true,\"bindings\":["
      "{\"key\":7,\"media\":\"vol_up\"},{\"key\":6,\"media\":\"vol_down\"},"
      "{\"key\":8,\"media\":\"mute\"},{\"key\":2,\"mods\":[\"win\"],\"code\":\"f13\"}]}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL_UINT8(4, cmd.fallback.count);

  FallbackBinding slots[kFallbackSlots];
  slots[4].code = 0x10;
  cmd.fallback.applyTo(slots);
  TEST_ASSERT_TRUE(slots[4].empty());  // replace wyczyścił
  TEST_ASSERT_EQUAL_UINT16(kConsumerVolUp, slots[6].media);
  TEST_ASSERT_EQUAL_UINT16(kConsumerVolDown, slots[5].media);
  TEST_ASSERT_EQUAL_UINT16(kConsumerMute, slots[7].media);
  TEST_ASSERT_EQUAL_UINT8(kModLGui, slots[1].mods);
  TEST_ASSERT_EQUAL_UINT8(0x68, slots[1].code);
}

void test_fallback_errors() {
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"set_fallback\",\"key\":9,\"code\":\"a\"}").status);
  // ChocPilot nie ma pokrętła – sloty enc_cw / enc_ccw są nieznane.
  TEST_ASSERT_EQUAL(ParseStatus::Invalid,
                    parse("{\"type\":\"set_fallback\",\"key\":\"enc_cw\",\"media\":\"mute\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"set_fallback\",\"key\":1,\"code\":\"nope\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"set_fallback\",\"key\":1,\"mods\":[\"hyper\"]}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"set_fallback\",\"key\":1,\"code\":\"a\",\"media\":\"mute\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"set_fallback\"}").status);
  // Pusty wpis czyści przypisanie.
  TEST_ASSERT_EQUAL(ParseStatus::Ok, parse("{\"type\":\"set_fallback\",\"key\":5}").status);
  TEST_ASSERT_TRUE(cmd.fallback.bindings[0].empty());
}

void test_reboot_and_flags() {
  TEST_ASSERT_EQUAL(ParseStatus::Ok, parse("{\"type\":\"reboot\",\"bootloader\":true}").status);
  TEST_ASSERT_EQUAL(CommandType::Reboot, cmd.type);
  TEST_ASSERT_TRUE(cmd.flag);
  TEST_ASSERT_EQUAL(ParseStatus::Ok, parse("{\"type\":\"reboot\"}").status);
  TEST_ASSERT_FALSE(cmd.flag);
  TEST_ASSERT_EQUAL(ParseStatus::Ok, parse("{\"type\":\"test_mode\"}").status);
  TEST_ASSERT_TRUE(cmd.flag);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"debug\",\"enable\":\"yes\"}").status);
}

void test_build_messages() {
  char buf[256];
  size_t n = buildKey(buf, sizeof(buf), 3, true, 1234);
  TEST_ASSERT_EQUAL_STRING("{\"type\":\"key\",\"key\":3,\"action\":\"down\",\"t\":1234}", buf);
  TEST_ASSERT_EQUAL(strlen(buf), n);
  buildAck(buf, sizeof(buf), 7);
  TEST_ASSERT_EQUAL_STRING("{\"type\":\"ack\",\"id\":7}", buf);
  buildError(buf, sizeof(buf), false, 0, "invalid json");
  TEST_ASSERT_EQUAL_STRING("{\"type\":\"error\",\"msg\":\"invalid json\"}", buf);
  buildHello(buf, sizeof(buf), "chocpilot", "1.0.0", false);
  TEST_ASSERT_EQUAL_STRING(
      "{\"type\":\"hello\",\"device\":\"chocpilot\",\"fw\":\"1.0.0\",\"board\":\"chocpilot\","
      "\"keys\":8,\"encoder\":false,\"hid\":true,\"online\":false,\"max_line\":272}",
      buf);
  // Za mały bufor → 0.
  TEST_ASSERT_EQUAL(0, buildHello(buf, 10, "chocpilot", "1.0.0", false));
}

void test_build_controls_messages() {
  char buf[256];
  buildHello(buf, sizeof(buf), "chocpilot", "1.1.0", false, true);
  TEST_ASSERT_NOT_NULL(strstr(buf, "\"board\":\"chocpilot\""));
  TEST_ASSERT_NOT_NULL(strstr(buf, "\"encoder\":true"));

  buildEncoder(buf, sizeof(buf), 1, -3, 500);
  TEST_ASSERT_EQUAL_STRING("{\"type\":\"encoder\",\"index\":1,\"delta\":-3,\"t\":500}", buf);
  buildEncoderKey(buf, sizeof(buf), 2, true, 501);
  TEST_ASSERT_EQUAL_STRING("{\"type\":\"encoder_key\",\"index\":2,\"action\":\"down\",\"t\":501}",
                           buf);
  buildSlider(buf, sizeof(buf), 100, 502);
  TEST_ASSERT_EQUAL_STRING("{\"type\":\"slider\",\"value\":100,\"t\":502}", buf);
  TEST_ASSERT_EQUAL(0, buildSlider(buf, 10, 42, 0));
}

void test_hid_codes() {
  TEST_ASSERT_EQUAL_UINT8(0x04, hidKeyFromName("a"));
  TEST_ASSERT_EQUAL_UINT8(0x1D, hidKeyFromName("Z"));
  TEST_ASSERT_EQUAL_UINT8(0x27, hidKeyFromName("0"));
  TEST_ASSERT_EQUAL_UINT8(0x3A, hidKeyFromName("f1"));
  TEST_ASSERT_EQUAL_UINT8(0x45, hidKeyFromName("f12"));
  TEST_ASSERT_EQUAL_UINT8(0x68, hidKeyFromName("f13"));
  TEST_ASSERT_EQUAL_UINT8(0x73, hidKeyFromName("F24"));
  TEST_ASSERT_EQUAL_UINT8(0, hidKeyFromName("f25"));
  TEST_ASSERT_EQUAL_UINT8(0x28, hidKeyFromName("enter"));
  TEST_ASSERT_EQUAL_UINT8(0x62, hidKeyFromName("kp_0"));
  TEST_ASSERT_EQUAL_UINT8(0x38, hidKeyFromName("/"));
  TEST_ASSERT_EQUAL_UINT8(kModRAlt, hidModFromName("ralt"));
  TEST_ASSERT_EQUAL_UINT16(kConsumerPlayPause, consumerFromName("play_pause"));
  TEST_ASSERT_EQUAL_UINT16(0, consumerFromName("louder"));
  // Koniec i środek tabel nazw (w wersji kompaktowej – jeden napis „nazwa\0nazwa\0…”).
  TEST_ASSERT_EQUAL_UINT8(0x31, hidKeyFromName("\\"));
  TEST_ASSERT_EQUAL_UINT8(0x33, hidKeyFromName(";"));
  TEST_ASSERT_EQUAL_UINT8(0x38, hidKeyFromName("slash"));
  TEST_ASSERT_EQUAL_UINT8(0x65, hidKeyFromName("MENU"));
  TEST_ASSERT_EQUAL_UINT8(0, hidKeyFromName("ent"));
  TEST_ASSERT_EQUAL_UINT8(kModRGui, hidModFromName("rgui"));
  TEST_ASSERT_EQUAL_UINT8(kModLCtrl, hidModFromName("Control"));
  TEST_ASSERT_EQUAL_UINT16(kConsumerMute, consumerFromName("mute"));
}

void test_string_escapes_and_numbers() {
  // Znaki ucieczki i \u (także para surogatów) dekodowane do UTF-8.
  ParseResult r = parse("{\"type\":\"flash\",\"text\":\"a\\\"b\\\\c\\u0105\\ud83d\\ude00\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL_STRING("a\"b\\c\xC4\x85\xF0\x9F\x98\x80", cmd.flash.text);
  // Liczby: ujemne, poza zakresem int32, z częścią ułamkową.
  r = parse("{\"type\":\"ping\",\"id\":-2147483648}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL_INT32(-2147483647 - 1, cmd.id);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"ping\",\"id\":2147483648}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"ping\",\"id\":1.5}").status);
  // Zagnieżdżone nieznane pola, spacje i null.
  r = parse(" { \"x\" : [ {\"a\":[1,2,{}]}, \"}\" ] , \"type\" : \"settings\" , \"flip\" : null ,"
            " \"brightness\" : 7 } ");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL_UINT16(SettingsPatch::kBrightness, cmd.settings.mask);
  // Błędy składni.
  TEST_ASSERT_EQUAL(ParseStatus::BadJson, parse("{\"type\":\"ping\"").status);
  TEST_ASSERT_EQUAL(ParseStatus::BadJson, parse("{\"type\":\"ping\",}").status);
  TEST_ASSERT_EQUAL(ParseStatus::BadJson, parse("{\"type\":\"pi\\x\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::BadJson, parse("").status);
}

void test_config_roundtrip() {
  DeviceConfig cfg;
  cfg.setDefaults();
  cfg.settings.brightness = 42;
  cfg.settings.flip = true;
  cfg.fallback[0].mods = kModLCtrl;
  cfg.fallback[0].code = 0x06;
  cfg.display.mode = DisplayMode::Grid;
  copyUtf8(cfg.display.title, sizeof(cfg.display.title), "Stream", kTitleChars);
  copyUtf8(cfg.display.labels[4], kLabelBuf, "Mic", kLabelChars);

  char buf[1536];
  const size_t n = encodeConfig(cfg, buf, sizeof(buf));
  TEST_ASSERT_TRUE(n > 0);

  DeviceConfig back;
  TEST_ASSERT_TRUE(decodeConfig(buf, n, back));
  TEST_ASSERT_EQUAL_UINT8(42, back.settings.brightness);
  TEST_ASSERT_TRUE(back.settings.flip);
  TEST_ASSERT_EQUAL_UINT8(kModLCtrl, back.fallback[0].mods);
  TEST_ASSERT_EQUAL_UINT16(kConsumerMute, back.fallback[7].media);
  TEST_ASSERT_EQUAL(DisplayMode::Grid, back.display.mode);
  TEST_ASSERT_EQUAL_STRING("Stream", back.display.title);
  TEST_ASSERT_EQUAL_STRING("Mic", back.display.labels[4]);
}

void test_config_corrupted_uses_defaults() {
  DeviceConfig cfg;
  TEST_ASSERT_FALSE(decodeConfig("{garbage", 8, cfg));
  TEST_ASSERT_EQUAL_UINT8(128, cfg.settings.brightness);
  TEST_ASSERT_EQUAL_UINT16(kConsumerVolUp, cfg.fallback[5].media);
}

void test_debouncer() {
  Debouncer d;
  d.reset(false, 0);
  TEST_ASSERT_FALSE(d.update(true, 1, 8));   // początek zmiany
  TEST_ASSERT_FALSE(d.update(false, 2, 8));  // drganie – reset czasu
  TEST_ASSERT_FALSE(d.update(true, 3, 8));
  TEST_ASSERT_FALSE(d.update(true, 10, 8));  // 7 ms stabilnie – za mało
  TEST_ASSERT_TRUE(d.update(true, 11, 8));   // 8 ms → wciśnięty
  TEST_ASSERT_TRUE(d.pressed());
  TEST_ASSERT_FALSE(d.update(true, 50, 8));  // bez zmian
  TEST_ASSERT_FALSE(d.update(false, 51, 8));
  TEST_ASSERT_TRUE(d.update(false, 59, 8));
  TEST_ASSERT_FALSE(d.pressed());
}

void test_elapsed_handles_future_and_wraparound() {
  TEST_ASSERT_FALSE(elapsed(1000, 1001, 3000));  // znacznik o 1 ms „z przyszłości” – nie timeout
  TEST_ASSERT_FALSE(elapsed(3999, 1000, 3000));
  TEST_ASSERT_TRUE(elapsed(4000, 1000, 3000));
  TEST_ASSERT_FALSE(elapsed(5, 0xFFFFFFF0u, 3000));  // przepełnienie millis()
  TEST_ASSERT_TRUE(elapsed(3000, 0xFFFFFFF0u, 3000));
}

void test_leds_command() {
  ParseResult r = parse(
      "{\"type\":\"leds\",\"id\":7,\"mode\":\"breathe\",\"color\":\"#ff8000\",\"brightness\":200,"
      "\"speed\":9,\"react\":false}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL(CommandType::Leds, cmd.type);
  TEST_ASSERT_TRUE(cmd.leds.save);  // domyślnie zapis do pamięci
  TEST_ASSERT_EQUAL(LedMode::Breathe, cmd.leds.values.mode);
  TEST_ASSERT_EQUAL_UINT8(0xFF, cmd.leds.values.r);
  TEST_ASSERT_EQUAL_UINT8(0x80, cmd.leds.values.g);
  TEST_ASSERT_EQUAL_UINT8(0x00, cmd.leds.values.b);

  LedSettings s;
  cmd.leds.applyTo(s);
  TEST_ASSERT_EQUAL_UINT8(200, s.brightness);
  TEST_ASSERT_EQUAL_UINT8(9, s.speed);
  TEST_ASSERT_FALSE(s.react);

  // częściowa zmiana bez zapisu: tylko kolor
  r = parse("{\"type\":\"leds\",\"color\":\"#00FF00\",\"save\":false}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_FALSE(cmd.leds.save);
  cmd.leds.applyTo(s);
  TEST_ASSERT_EQUAL(LedMode::Breathe, s.mode);
  TEST_ASSERT_EQUAL_UINT8(0xFF, s.g);
  TEST_ASSERT_EQUAL_UINT8(200, s.brightness);

  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"leds\",\"mode\":\"disco\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"leds\",\"color\":\"#12345\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"leds\",\"color\":\"#12345G\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"leds\",\"speed\":0}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"leds\",\"brightness\":256}").status);
}

void test_hello_reports_leds() {
  char buf[256];
  buildHello(buf, sizeof(buf), "chocpilot", "1.1.0", true, true, 12);
  TEST_ASSERT_NOT_NULL(strstr(buf, "\"leds\":12"));
  buildHello(buf, sizeof(buf), "chocpilot", "1.1.0", true);  // bez diod i animacji
  TEST_ASSERT_NULL(strstr(buf, "\"leds\""));
}

void test_config_v1_keeps_settings() {
  // Zapis sprzed LED (wersja 1): ta sama struktura bez końcowego pola leds.
  DeviceConfig cfg;
  cfg.setDefaults();
  cfg.settings.brightness = 33;
  char buf[1536];
  const size_t n = encodeConfig(cfg, buf, sizeof(buf));
  const size_t v1Fields = offsetof(DeviceConfig, leds);
  const size_t v1Size = (v1Fields + alignof(DeviceConfig) - 1) / alignof(DeviceConfig) *
                        alignof(DeviceConfig);
  TEST_ASSERT_TRUE(n > 1 + v1Size);
  buf[0] = 1;
  DeviceConfig back;
  TEST_ASSERT_TRUE(decodeConfig(buf, 1 + v1Size, back));
  TEST_ASSERT_EQUAL_UINT8(33, back.settings.brightness);
  TEST_ASSERT_EQUAL(LedMode::Status, back.leds.mode);  // domyślne LED

  // wersja 2 przenosi ustawienia LED
  cfg.leds.mode = LedMode::Rainbow;
  cfg.leds.speed = 3;
  const size_t n2 = encodeConfig(cfg, buf, sizeof(buf));
  TEST_ASSERT_TRUE(decodeConfig(buf, n2, back));
  TEST_ASSERT_EQUAL(LedMode::Rainbow, back.leds.mode);
  TEST_ASSERT_EQUAL_UINT8(3, back.leds.speed);
}

void test_led_effects() {
  LedSettings s;
  s.mode = LedMode::Static;
  s.r = 255;
  s.g = 0;
  s.b = 0;
  s.brightness = 255;
  LedFrame f;
  f.now = 1000;
  f.online = true;
  Rgb out[12];

  renderLeds(s, f, out, 12);
  TEST_ASSERT_EQUAL_UINT8(kLedMaxLevel, out[0].r);  // pełna jasność = limit prądu
  TEST_ASSERT_EQUAL_UINT8(0, out[11].g);

  // wygaszacz i tryb off gaszą wszystko
  f.sleeping = true;
  renderLeds(s, f, out, 12);
  TEST_ASSERT_EQUAL_UINT8(0, out[0].r);
  f.sleeping = false;
  s.mode = LedMode::Off;
  renderLeds(s, f, out, 12);
  TEST_ASSERT_EQUAL_UINT8(0, out[5].r);

  // status: offline = bursztyn (czerwony > niebieski)
  s.mode = LedMode::Status;
  f.online = false;
  renderLeds(s, f, out, 12);
  TEST_ASSERT_TRUE(out[0].r > out[0].b);

  // oddychanie: najjaśniej w połowie okresu, najciemniej na początku
  s.mode = LedMode::Breathe;
  s.speed = 1;  // okres 6 s
  f.now = 0;
  renderLeds(s, f, out, 12);
  const uint8_t dim = out[0].r;
  f.now = 3000;
  renderLeds(s, f, out, 12);
  TEST_ASSERT_TRUE(out[0].r > dim * 4);

  // tęcza: sąsiednie diody mają różne kolory
  s.mode = LedMode::Rainbow;
  renderLeds(s, f, out, 12);
  TEST_ASSERT_FALSE(out[0].r == out[4].r && out[0].g == out[4].g && out[0].b == out[4].b);

  // błysk klawisza K3 → dioda 10, wygasa po kLedReactMs
  s.mode = LedMode::Static;
  s.r = 0;
  s.react = true;
  const uint8_t keyLed[8] = {8, 9, 10, 11, 5, 4, 3, 2};
  uint32_t downAt[8] = {0};
  downAt[2] = 5000;
  f.keyDownAt = downAt;
  f.keyLed = keyLed;
  f.reactMask = 1u << 2;
  f.now = 5000;
  uint8_t active = renderLeds(s, f, out, 12);
  TEST_ASSERT_EQUAL_UINT8(1u << 2, active);
  TEST_ASSERT_EQUAL_UINT8(kLedMaxLevel, out[10].b);  // pełna biel (po limicie jasności)
  TEST_ASSERT_EQUAL_UINT8(0, out[9].b);
  f.now = 5000 + kLedReactMs;
  active = renderLeds(s, f, out, 12);
  TEST_ASSERT_EQUAL_UINT8(0, active);
  TEST_ASSERT_EQUAL_UINT8(0, out[10].b);

  TEST_ASSERT_EQUAL_UINT8(255, hueToRgb(0).r);
  TEST_ASSERT_EQUAL_UINT8(255, hueToRgb(86).g);
}

void test_settings_saver() {
  ParseResult r = parse("{\"type\":\"settings\",\"saver\":\"corgi\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_TRUE(cmd.settings.mask & SettingsPatch::kSaver);
  TEST_ASSERT_EQUAL_STRING("corgi", cmd.settings.saver);
  r = parse("{\"type\":\"settings\",\"saver\":\"off\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL_STRING("", cmd.settings.saver);  // off = wygaszony ekran
  r = parse("{\"type\":\"settings\",\"brightness\":10}");
  TEST_ASSERT_FALSE(cmd.settings.mask & SettingsPatch::kSaver);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"settings\",\"saver\":5}").status);
  // za długa nazwa jest obcinana do 11 znaków
  parse("{\"type\":\"settings\",\"saver\":\"abcdefghijklmnop\"}");
  TEST_ASSERT_EQUAL_STRING("abcdefghijk", cmd.settings.saver);
}

void test_hello_reports_savers() {
  char buf[256];
  const char* names[] = {"rabbit", "corgi"};
  buildHello(buf, sizeof(buf), "chocpilot", "1.1.0", true, true, 12, names, 2);
  TEST_ASSERT_NOT_NULL(strstr(buf, "\"savers\":[\"rabbit\",\"corgi\"]"));
  buildHello(buf, sizeof(buf), "chocpilot", "1.1.0", true);  // bez diod i animacji
  TEST_ASSERT_NULL(strstr(buf, "\"savers\""));
}

void test_config_v2_keeps_leds_and_v3_keeps_saver() {
  DeviceConfig cfg;
  cfg.setDefaults();
  cfg.leds.mode = LedMode::Breathe;
  copyUtf8(cfg.saver.name, sizeof(cfg.saver.name), "rabbit", kSaverNameBuf - 1);
  char buf[1536];
  const size_t n = encodeConfig(cfg, buf, sizeof(buf));
  DeviceConfig back;
  TEST_ASSERT_TRUE(decodeConfig(buf, n, back));
  TEST_ASSERT_EQUAL_STRING("rabbit", back.saver.name);
  TEST_ASSERT_EQUAL(LedMode::Breathe, back.leds.mode);

  // zapis wersji 2 (bez saver): LED zostają, wygaszacz domyślny (pusty)
  const size_t v2Fields = offsetof(DeviceConfig, saver);
  const size_t v2Size =
      (v2Fields + alignof(DeviceConfig) - 1) / alignof(DeviceConfig) * alignof(DeviceConfig);
  buf[0] = 2;
  TEST_ASSERT_TRUE(decodeConfig(buf, 1 + v2Size, back));
  TEST_ASSERT_EQUAL(LedMode::Breathe, back.leds.mode);
  TEST_ASSERT_EQUAL_STRING("", back.saver.name);
}

void test_time_command_and_wall_clock() {
  ParseResult r = parse("{\"type\":\"time\",\"hour\":23,\"minute\":59,\"second\":30}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL(CommandType::Time, cmd.type);
  TEST_ASSERT_EQUAL_UINT8(23, cmd.time.hour);
  TEST_ASSERT_EQUAL_UINT8(59, cmd.time.minute);
  TEST_ASSERT_EQUAL_UINT8(30, cmd.time.second);
  TEST_ASSERT_EQUAL(ParseStatus::Ok, parse("{\"type\":\"time\",\"hour\":7,\"minute\":5}").status);
  TEST_ASSERT_EQUAL_UINT8(0, cmd.time.second);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"time\",\"hour\":24,\"minute\":0}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"time\",\"hour\":1}").status);

  WallClock clock;
  uint8_t h = 0, m = 0;
  TEST_ASSERT_FALSE(clock.now(0, h, m));  // bez czasu z aplikacji – brak zegara
  clock.set(23, 59, 30, 0xFFFFF000UL);    // tuż przed przepełnieniem millis()
  TEST_ASSERT_TRUE(clock.now(0xFFFFF000UL + 29000, h, m));
  TEST_ASSERT_EQUAL_UINT8(23, h);
  TEST_ASSERT_EQUAL_UINT8(59, m);
  TEST_ASSERT_TRUE(clock.now(0xFFFFF000UL + 31000, h, m));  // przez północ i przepełnienie
  TEST_ASSERT_EQUAL_UINT8(0, h);
  TEST_ASSERT_EQUAL_UINT8(0, m);
  TEST_ASSERT_TRUE(clock.now(0xFFFFF000UL + 31000 + 90UL * 60 * 1000, h, m));
  TEST_ASSERT_EQUAL_UINT8(1, h);
  TEST_ASSERT_EQUAL_UINT8(30, m);
}

void test_icon_command_and_base64() {
  uint8_t out[8];
  TEST_ASSERT_EQUAL_INT(3, decodeBase64("AQID", 4, out, sizeof(out)));
  TEST_ASSERT_EQUAL_UINT8(1, out[0]);
  TEST_ASSERT_EQUAL_UINT8(3, out[2]);
  TEST_ASSERT_EQUAL_INT(1, decodeBase64("/w==", 4, out, sizeof(out)));
  TEST_ASSERT_EQUAL_UINT8(0xFF, out[0]);
  TEST_ASSERT_EQUAL_INT(-1, decodeBase64("AQI", 3, out, sizeof(out)));   // zła długość
  TEST_ASSERT_EQUAL_INT(-1, decodeBase64("A=QI", 4, out, sizeof(out)));  // znak po '='
  TEST_ASSERT_EQUAL_INT(-1, decodeBase64("AQIDBAUG", 8, out, 4));        // brak miejsca

  ParseResult r = parse("{\"type\":\"icon\",\"key\":3,\"offset\":128,\"data\":\"AQIDBA==\"}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_EQUAL(CommandType::Icon, cmd.type);
  TEST_ASSERT_EQUAL_UINT8(3, cmd.icon.key);
  TEST_ASSERT_EQUAL_UINT16(128, cmd.icon.offset);
  TEST_ASSERT_EQUAL_UINT8(4, cmd.icon.len);
  TEST_ASSERT_EQUAL_UINT8(4, cmd.icon.data[3]);
  TEST_ASSERT_FALSE(cmd.icon.clear);
  r = parse("{\"type\":\"icon\",\"key\":8,\"clear\":true}");
  TEST_ASSERT_EQUAL(ParseStatus::Ok, r.status);
  TEST_ASSERT_TRUE(cmd.icon.clear);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"icon\",\"key\":9,\"data\":\"AA==\"}").status);
  TEST_ASSERT_EQUAL(ParseStatus::Invalid, parse("{\"type\":\"icon\",\"key\":1,\"data\":\"!!!!\"}").status);
  // kawałek wychodzący poza 544 B ikony
  TEST_ASSERT_EQUAL(ParseStatus::Invalid,
                    parse("{\"type\":\"icon\",\"key\":1,\"offset\":543,\"data\":\"AQID\"}").status);

  char buf[256];
  buildHello(buf, sizeof(buf), "chocpilot", "1.1.0", true, true, 12, nullptr, 0, 32);
  TEST_ASSERT_NOT_NULL(strstr(buf, "\"icon\":32"));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_invalid_json);
  RUN_TEST(test_unknown_type_is_ignored);
  RUN_TEST(test_ping_with_id_and_unknown_fields);
  RUN_TEST(test_hello_without_id);
  RUN_TEST(test_display_grid);
  RUN_TEST(test_display_utf8_truncation);
  RUN_TEST(test_display_bar_and_text);
  RUN_TEST(test_display_errors);
  RUN_TEST(test_flash);
  RUN_TEST(test_settings_partial);
  RUN_TEST(test_settings_validation);
  RUN_TEST(test_fallback_single);
  RUN_TEST(test_fallback_list_and_replace);
  RUN_TEST(test_fallback_errors);
  RUN_TEST(test_reboot_and_flags);
  RUN_TEST(test_build_messages);
  RUN_TEST(test_build_controls_messages);
  RUN_TEST(test_leds_command);
  RUN_TEST(test_hello_reports_leds);
  RUN_TEST(test_config_v1_keeps_settings);
  RUN_TEST(test_led_effects);
  RUN_TEST(test_settings_saver);
  RUN_TEST(test_time_command_and_wall_clock);
  RUN_TEST(test_icon_command_and_base64);
  RUN_TEST(test_hello_reports_savers);
  RUN_TEST(test_config_v2_keeps_leds_and_v3_keeps_saver);
  RUN_TEST(test_hid_codes);
  RUN_TEST(test_string_escapes_and_numbers);
  RUN_TEST(test_config_roundtrip);
  RUN_TEST(test_config_corrupted_uses_defaults);
  RUN_TEST(test_debouncer);
  RUN_TEST(test_elapsed_handles_future_and_wraparound);
  return UNITY_END();
}
