// Kodek protokołu bez ArduinoJson dla płytek z małą pamięcią (CHOCPILOT_COMPACT, ATmega32U4).
// Parser czyta linię w miejscu, bez alokacji i drzewa dokumentu: najpierw sprawdza składnię
// całej wartości, potem wyszukuje pola po nazwie. Wiadomości wychodzące składa ręcznie.
// Zachowanie jest takie samo jak w protocol_codec.cpp – te same testy (środowisko native_compact).
#if defined(CHOCPILOT_COMPACT)

#include <string.h>

#include "flash_text.h"
#include "hid_codes.h"
#include "protocol_codec.h"

namespace chocpilot {

namespace {

constexpr uint32_t kMaxDisplayMs = 600000;
constexpr uint32_t kMaxFlashMs = 10000;
constexpr uint8_t kMaxNesting = 10;  // jak domyślny limit ArduinoJson
constexpr size_t kNameBuf = 16;      // nazwy klawiszy, modyfikatorów i multimediów

ParseResult invalid(FlashText msg) { return ParseResult{ParseStatus::Invalid, msg}; }
ParseResult ok() { return ParseResult{ParseStatus::Ok, nullptr}; }

// --- czytanie JSON ---
// Wartość to wskaźnik na jej pierwszy znak w linii; nullptr = brak pola (albo null).
// Koniec analizowanej linii – wspólny dla jednego wywołania parseCommand().
const char* gEnd = nullptr;

bool isDigit(char c) { return c >= '0' && c <= '9'; }

int8_t hexValue(char c) {
  if (isDigit(c)) return static_cast<int8_t>(c - '0');
  if (c >= 'a' && c <= 'f') return static_cast<int8_t>(c - 'a' + 10);
  if (c >= 'A' && c <= 'F') return static_cast<int8_t>(c - 'A' + 10);
  return -1;
}

const char* skipWs(const char* p) {
  while (p < gEnd && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) ++p;
  return p;
}

// Funkcje skip* zwracają pozycję za wartością albo nullptr przy błędzie składni.
const char* skipString(const char* p) {
  for (++p; p < gEnd; ++p) {
    const char c = *p;
    if (c == '"') return p + 1;
    if (c == '\\') {
      if (++p >= gEnd) return nullptr;
      if (*p == 'u') {
        for (uint8_t i = 0; i < 4; ++i) {
          if (++p >= gEnd || hexValue(*p) < 0) return nullptr;
        }
      } else if (*p == '\0' || strchr("\"\\/bfnrt", *p) == nullptr) {
        return nullptr;  // nieznana sekwencja ucieczki
      }
    } else if (static_cast<uint8_t>(c) < 0x20) {
      return nullptr;
    }
  }
  return nullptr;
}

const char* skipDigits(const char* p) {
  const char* start = p;
  while (p < gEnd && isDigit(*p)) ++p;
  return p > start ? p : nullptr;
}

const char* skipNumber(const char* p) {
  if (*p == '-') ++p;
  p = skipDigits(p);
  if (p != nullptr && p < gEnd && *p == '.') p = skipDigits(p + 1);
  if (p != nullptr && p < gEnd && (*p == 'e' || *p == 'E')) {
    ++p;
    if (p < gEnd && (*p == '+' || *p == '-')) ++p;
    p = skipDigits(p);
  }
  return p;
}

const char* skipWord(const char* p, const char* wordP) {
  for (; pgmByte(wordP) != 0; ++wordP, ++p) {
    if (p >= gEnd || static_cast<uint8_t>(*p) != pgmByte(wordP)) return nullptr;
  }
  return p;
}

const char* skipValue(const char* p, uint8_t depth);

// Obiekt { "klucz": wartość, ... } albo tablica [ wartość, ... ].
const char* skipContainer(const char* p, uint8_t depth) {
  if (depth >= kMaxNesting) return nullptr;
  const bool object = *p == '{';
  const char close = object ? '}' : ']';
  p = skipWs(p + 1);
  if (p < gEnd && *p == close) return p + 1;
  while (p < gEnd) {
    if (object) {
      if (*p != '"') return nullptr;
      p = skipString(p);
      if (p == nullptr) return nullptr;
      p = skipWs(p);
      if (p >= gEnd || *p != ':') return nullptr;
      p = skipWs(p + 1);
    }
    p = skipValue(p, static_cast<uint8_t>(depth + 1));
    if (p == nullptr) return nullptr;
    p = skipWs(p);
    if (p >= gEnd) return nullptr;
    if (*p == close) return p + 1;
    if (*p != ',') return nullptr;
    p = skipWs(p + 1);
  }
  return nullptr;
}

const char* skipValue(const char* p, uint8_t depth) {
  if (p >= gEnd) return nullptr;
  switch (*p) {
    case '"':
      return skipString(p);
    case '{':
    case '[':
      return skipContainer(p, depth);
    case 't':
      return skipWord(p, CHOCPILOT_P("true"));
    case 'f':
      return skipWord(p, CHOCPILOT_P("false"));
    case 'n':
      return skipWord(p, CHOCPILOT_P("null"));
    default:
      return (*p == '-' || isDigit(*p)) ? skipNumber(p) : nullptr;
  }
}

// Poniższe funkcje działają na linii o już sprawdzonej składni.

// Wartość pola `keyP` (nazwa w pamięci programu) w obiekcie `obj` (wskazuje '{').
// null zwraca jako brak pola – jak isNull() w ArduinoJson.
const char* member(const char* obj, const char* keyP) {
  const char* p = skipWs(obj + 1);
  while (p < gEnd && *p == '"') {
    const char* keyEnd = skipString(p);
    const bool match = equalsP(p + 1, static_cast<size_t>(keyEnd - p - 2), keyP);
    p = skipWs(skipWs(keyEnd) + 1);
    if (match) return *p == 'n' ? nullptr : p;
    p = skipWs(skipValue(p, 0));
    if (*p != ',') break;
    p = skipWs(p + 1);
  }
  return nullptr;
}

const char* arrayFirst(const char* arr) {
  const char* p = skipWs(arr + 1);
  return *p == ']' ? nullptr : p;
}

const char* arrayNext(const char* item) {
  const char* p = skipWs(skipValue(item, 0));
  return *p == ',' ? skipWs(p + 1) : nullptr;
}

size_t arraySize(const char* arr) {
  size_t n = 0;
  for (const char* item = arrayFirst(arr); item != nullptr; item = arrayNext(item)) ++n;
  return n;
}

bool isString(const char* v) { return v != nullptr && *v == '"'; }
bool isArray(const char* v) { return v != nullptr && *v == '['; }
bool isObject(const char* v) { return v != nullptr && *v == '{'; }
bool isBool(const char* v) { return v != nullptr && (*v == 't' || *v == 'f'); }

// Czy napis (bez sekwencji ucieczki) równa się słowu z pamięci programu?
bool stringIs(const char* v, const char* wordP) {
  return equalsP(v + 1, static_cast<size_t>(skipString(v) - v - 2), wordP);
}

// Liczba całkowita z zakresu int32 (bez części ułamkowej i wykładnika); false = inny typ.
bool readInt32(const char* v, int32_t& out) {
  if (v == nullptr || !(*v == '-' || isDigit(*v))) return false;
  const bool negative = *v == '-';
  const char* p = negative ? v + 1 : v;
  uint32_t value = 0;
  for (; p < gEnd && isDigit(*p); ++p) {
    const uint8_t d = static_cast<uint8_t>(*p - '0');
    if (value > (0x80000000UL - d) / 10) return false;
    value = value * 10 + d;
  }
  if (p < gEnd && (*p == '.' || *p == 'e' || *p == 'E')) return false;
  if (negative) {
    out = value == 0 ? 0 : -static_cast<int32_t>(value - 1) - 1;
  } else {
    if (value > 0x7FFFFFFFUL) return false;
    out = static_cast<int32_t>(value);
  }
  return true;
}

uint8_t encodeUtf8(uint32_t c, char* out) {
  if (c < 0x80) {
    out[0] = static_cast<char>(c);
    return 1;
  }
  if (c < 0x800) {
    out[0] = static_cast<char>(0xC0 | (c >> 6));
    out[1] = static_cast<char>(0x80 | (c & 0x3F));
    return 2;
  }
  if (c < 0x10000) {
    out[0] = static_cast<char>(0xE0 | (c >> 12));
    out[1] = static_cast<char>(0x80 | ((c >> 6) & 0x3F));
    out[2] = static_cast<char>(0x80 | (c & 0x3F));
    return 3;
  }
  out[0] = static_cast<char>(0xF0 | (c >> 18));
  out[1] = static_cast<char>(0x80 | ((c >> 12) & 0x3F));
  out[2] = static_cast<char>(0x80 | ((c >> 6) & 0x3F));
  out[3] = static_cast<char>(0x80 | (c & 0x3F));
  return 4;
}

uint16_t hex4(const char* p) {
  uint16_t value = 0;
  for (uint8_t i = 0; i < 4; ++i) value = static_cast<uint16_t>(value << 4 | hexValue(p[i]));
  return value;
}

// Dekoduje napis JSON (v wskazuje '"') do dst, obcinając jak copyUtf8(): najwyżej maxChars
// znaków i cap−1 bajtów, bez łamania sekwencji UTF-8.
void readString(const char* v, char* dst, size_t cap, size_t maxChars) {
  size_t out = 0;
  size_t chars = 0;
  const char* p = v + 1;
  while (*p != '"' && chars < maxChars) {
    char seq[4];
    uint8_t len = 0;
    if (*p == '\\') {
      const char e = p[1];
      p += 2;
      uint32_t c = static_cast<uint8_t>(e);
      switch (e) {
        case 'b':
          c = '\b';
          break;
        case 'f':
          c = '\f';
          break;
        case 'n':
          c = '\n';
          break;
        case 'r':
          c = '\r';
          break;
        case 't':
          c = '\t';
          break;
        case 'u':
          c = hex4(p);
          p += 4;
          if (c >= 0xD800 && c <= 0xDBFF && p[0] == '\\' && p[1] == 'u') {
            const uint16_t low = hex4(p + 2);
            if (low >= 0xDC00 && low <= 0xDFFF) {
              c = 0x10000 + ((c - 0xD800) << 10) + (low - 0xDC00);
              p += 6;
            }
          }
          if (c >= 0xD800 && c <= 0xDFFF) c = '?';  // samotny surogat
          break;
        default:  // \" \\ \/
          break;
      }
      if (c == 0) break;
      len = encodeUtf8(c, seq);
    } else {
      const uint8_t lead = static_cast<uint8_t>(*p);
      uint8_t seqLen = 1;
      if ((lead & 0xE0) == 0xC0) {
        seqLen = 2;
      } else if ((lead & 0xF0) == 0xE0) {
        seqLen = 3;
      } else if ((lead & 0xF8) == 0xF0) {
        seqLen = 4;
      }
      while (len < seqLen && p[len] != '"') {
        seq[len] = p[len];
        ++len;
      }
      if (len < seqLen) break;  // niepełna sekwencja na końcu napisu
      p += len;
    }
    if (out + len >= cap) break;
    memcpy(dst + out, seq, len);
    out += len;
    ++chars;
  }
  if (cap > 0) dst[out] = '\0';
}

// --- pola komend ---

// Pobiera opcjonalny napis. Zwraca false (i ustawia err), gdy pole ma zły typ.
bool readStringField(const char* obj, const char* keyP, char* dst, size_t cap, size_t maxChars,
                     FlashText& err) {
  const char* v = member(obj, keyP);
  if (v == nullptr) return true;
  if (!isString(v)) {
    err = CHOCPILOT_F("string expected");
    return false;
  }
  readString(v, dst, cap, maxChars);
  return true;
}

// Pobiera opcjonalną liczbę całkowitą z zakresu [lo, hi].
bool readIntField(const char* obj, const char* keyP, int32_t lo, int32_t hi, int32_t& out,
                  bool& present, FlashText& err) {
  const char* v = member(obj, keyP);
  present = false;
  if (v == nullptr) return true;
  int32_t value = 0;
  if (!readInt32(v, value)) {
    err = CHOCPILOT_F("integer expected");
    return false;
  }
  if (value < lo || value > hi) {
    err = CHOCPILOT_F("value out of range");
    return false;
  }
  out = value;
  present = true;
  return true;
}

bool readBoolField(const char* obj, const char* keyP, bool& out, bool& present, FlashText& err) {
  const char* v = member(obj, keyP);
  present = false;
  if (v == nullptr) return true;
  if (!isBool(v)) {
    err = CHOCPILOT_F("boolean expected");
    return false;
  }
  out = *v == 't';
  present = true;
  return true;
}

ParseResult parseDisplay(const char* obj, DisplayCommand& d) {
  const char* mode = member(obj, CHOCPILOT_P("mode"));
  if (!isString(mode)) return invalid(CHOCPILOT_F("missing mode"));
  FlashText err = nullptr;
  int32_t value = 0;
  bool present = false;

  if (stringIs(mode, CHOCPILOT_P("profile"))) {
    d.mode = DisplayMode::Profile;
    if (!readStringField(obj, CHOCPILOT_P("name"), d.title, sizeof(d.title), kTitleChars, err)) {
      return invalid(err);
    }
    return ok();
  }
  if (stringIs(mode, CHOCPILOT_P("grid"))) {
    d.mode = DisplayMode::Grid;
    if (!readStringField(obj, CHOCPILOT_P("title"), d.title, sizeof(d.title), kTitleChars, err)) {
      return invalid(err);
    }
    const char* labels = member(obj, CHOCPILOT_P("labels"));
    if (labels != nullptr) {
      if (!isArray(labels)) return invalid(CHOCPILOT_F("labels must be an array"));
      if (arraySize(labels) > kMatrixKeys) return invalid(CHOCPILOT_F("too many labels"));
      uint8_t i = 0;
      for (const char* item = arrayFirst(labels); item != nullptr; item = arrayNext(item), ++i) {
        if (*item == 'n') continue;  // null
        if (!isString(item)) return invalid(CHOCPILOT_F("label must be a string"));
        readString(item, d.labels[i], kLabelBuf, kLabelChars);
      }
    }
    return ok();
  }
  if (stringIs(mode, CHOCPILOT_P("text"))) {
    d.mode = DisplayMode::Text;
    if (!readStringField(obj, CHOCPILOT_P("line1"), d.line1, sizeof(d.line1), kTitleChars, err) ||
        !readStringField(obj, CHOCPILOT_P("line2"), d.line2, sizeof(d.line2), kTitleChars, err)) {
      return invalid(err);
    }
  } else if (stringIs(mode, CHOCPILOT_P("bar"))) {
    d.mode = DisplayMode::Bar;
    if (!readStringField(obj, CHOCPILOT_P("title"), d.title, sizeof(d.title), kTitleChars, err)) {
      return invalid(err);
    }
    const char* v = member(obj, CHOCPILOT_P("value"));
    if (v != nullptr) {
      int32_t raw = 0;
      if (!readInt32(v, raw)) return invalid(CHOCPILOT_F("integer expected"));
      if (raw < 0) raw = 0;
      if (raw > 100) raw = 100;
      d.value = static_cast<uint8_t>(raw);
    }
  } else {
    return invalid(CHOCPILOT_F("unknown display mode"));
  }

  if (!readIntField(obj, CHOCPILOT_P("ms"), 0, static_cast<int32_t>(kMaxDisplayMs), value, present,
                    err)) {
    return invalid(err);
  }
  d.ms = present ? static_cast<uint32_t>(value) : 0;
  return ok();
}

ParseResult parseFlash(const char* obj, FlashCommand& f) {
  FlashText err = nullptr;
  int32_t value = 0;
  bool present = false;
  const char* text = member(obj, CHOCPILOT_P("text"));
  if (!isString(text)) return invalid(CHOCPILOT_F("missing text"));
  readString(text, f.text, sizeof(f.text), kTitleChars);
  if (!readIntField(obj, CHOCPILOT_P("key"), 1, kTotalKeys, value, present, err)) return invalid(err);
  f.key = present ? static_cast<uint8_t>(value) : 0;
  if (!readIntField(obj, CHOCPILOT_P("ms"), 1, static_cast<int32_t>(kMaxFlashMs), value, present,
                    err)) {
    return invalid(err);
  }
  f.ms = present ? static_cast<uint32_t>(value) : 1000;
  return ok();
}

ParseResult parseSettings(const char* obj, SettingsPatch& p) {
  FlashText err = nullptr;
  int32_t value = 0;
  bool present = false;
  bool flag = false;

  if (!readIntField(obj, CHOCPILOT_P("brightness"), 0, 255, value, present, err)) return invalid(err);
  if (present) {
    p.mask |= SettingsPatch::kBrightness;
    p.values.brightness = static_cast<uint8_t>(value);
  }
  if (!readIntField(obj, CHOCPILOT_P("screensaver_s"), 0, 65535, value, present, err)) {
    return invalid(err);
  }
  if (present) {
    p.mask |= SettingsPatch::kScreensaver;
    p.values.screensaverS = static_cast<uint16_t>(value);
  }
  if (!readBoolField(obj, CHOCPILOT_P("flip"), flag, present, err)) return invalid(err);
  if (present) {
    p.mask |= SettingsPatch::kFlip;
    p.values.flip = flag;
  }
  if (!readBoolField(obj, CHOCPILOT_P("enc_reverse"), flag, present, err)) return invalid(err);
  if (present) {
    p.mask |= SettingsPatch::kEncReverse;
    p.values.encReverse = flag;
  }
  if (!readIntField(obj, CHOCPILOT_P("enc_pulses"), 1, 8, value, present, err)) return invalid(err);
  if (present) {
    p.mask |= SettingsPatch::kEncPulses;
    p.values.encPulses = static_cast<uint8_t>(value);
  }
  if (!readIntField(obj, CHOCPILOT_P("debounce_ms"), 1, 50, value, present, err)) return invalid(err);
  if (present) {
    p.mask |= SettingsPatch::kDebounce;
    p.values.debounceMs = static_cast<uint8_t>(value);
  }
  if (!readIntField(obj, CHOCPILOT_P("oled_addr"), 0x08, 0x77, value, present, err)) {
    return invalid(err);
  }
  if (present) {
    p.mask |= SettingsPatch::kOledAddr;
    p.values.oledAddr = static_cast<uint8_t>(value);
  }
  return ok();
}

ParseResult parseBinding(const char* obj, uint8_t& slot, FallbackBinding& b) {
  char name[kNameBuf];
  int32_t number = 0;

  const char* key = member(obj, CHOCPILOT_P("key"));
  if (readInt32(key, number)) {
    if (number < 1 || number > kTotalKeys) return invalid(CHOCPILOT_F("key out of range"));
    slot = static_cast<uint8_t>(number - 1);
  } else if (isString(key)) {
    if (stringIs(key, CHOCPILOT_P("enc_cw"))) {
      slot = kSlotEncCw;
    } else if (stringIs(key, CHOCPILOT_P("enc_ccw"))) {
      slot = kSlotEncCcw;
    } else {
      return invalid(CHOCPILOT_F("unknown key"));
    }
  } else {
    return invalid(CHOCPILOT_F("missing key"));
  }

  b = FallbackBinding();
  const char* mods = member(obj, CHOCPILOT_P("mods"));
  if (isString(mods)) {
    readString(mods, name, sizeof(name), sizeof(name));
    b.mods = hidModFromName(name);
    if (b.mods == 0) return invalid(CHOCPILOT_F("unknown modifier"));
  } else if (isArray(mods)) {
    for (const char* m = arrayFirst(mods); m != nullptr; m = arrayNext(m)) {
      uint8_t bit = 0;
      if (isString(m)) {
        readString(m, name, sizeof(name), sizeof(name));
        bit = hidModFromName(name);
      }
      if (bit == 0) return invalid(CHOCPILOT_F("unknown modifier"));
      b.mods |= bit;
    }
  } else if (mods != nullptr) {
    return invalid(CHOCPILOT_F("mods must be an array"));
  }

  const char* code = member(obj, CHOCPILOT_P("code"));
  if (isString(code)) {
    readString(code, name, sizeof(name), sizeof(name));
    b.code = hidKeyFromName(name);
    if (b.code == 0) return invalid(CHOCPILOT_F("unknown key code"));
  } else if (readInt32(code, number)) {
    if (number < 1 || number > 255) return invalid(CHOCPILOT_F("code out of range"));
    b.code = static_cast<uint8_t>(number);
  } else if (code != nullptr) {
    return invalid(CHOCPILOT_F("bad code"));
  }

  const char* media = member(obj, CHOCPILOT_P("media"));
  if (isString(media)) {
    readString(media, name, sizeof(name), sizeof(name));
    b.media = consumerFromName(name);
    if (b.media == 0) return invalid(CHOCPILOT_F("unknown media key"));
  } else if (readInt32(media, number)) {
    if (number < 1 || number > 0x3FF) return invalid(CHOCPILOT_F("media out of range"));
    b.media = static_cast<uint16_t>(number);
  } else if (media != nullptr) {
    return invalid(CHOCPILOT_F("bad media"));
  }

  if (b.media != 0 && (b.code != 0 || b.mods != 0)) {
    return invalid(CHOCPILOT_F("use either code or media"));
  }
  return ok();
}

ParseResult parseFallback(const char* obj, FallbackPatch& p) {
  const char* replace = member(obj, CHOCPILOT_P("replace"));
  if (replace != nullptr) {
    if (!isBool(replace)) return invalid(CHOCPILOT_F("boolean expected"));
    p.replace = *replace == 't';
  }

  const char* bindings = member(obj, CHOCPILOT_P("bindings"));
  if (bindings != nullptr) {
    if (!isArray(bindings)) return invalid(CHOCPILOT_F("bindings must be an array"));
    if (arraySize(bindings) > kFallbackSlots) return invalid(CHOCPILOT_F("too many bindings"));
    for (const char* item = arrayFirst(bindings); item != nullptr; item = arrayNext(item)) {
      if (!isObject(item)) return invalid(CHOCPILOT_F("binding must be an object"));
      ParseResult r = parseBinding(item, p.slots[p.count], p.bindings[p.count]);
      if (r.status != ParseStatus::Ok) return r;
      ++p.count;
    }
    return ok();
  }

  if (member(obj, CHOCPILOT_P("key")) != nullptr) {
    ParseResult r = parseBinding(obj, p.slots[0], p.bindings[0]);
    if (r.status != ParseStatus::Ok) return r;
    p.count = 1;
    return ok();
  }

  if (!p.replace) return invalid(CHOCPILOT_F("missing key or bindings"));
  return ok();
}

ParseResult parseFlag(const char* obj, const char* keyP, bool defaultValue, bool& out) {
  const char* v = member(obj, keyP);
  if (v == nullptr) {
    out = defaultValue;
    return ok();
  }
  if (!isBool(v)) return invalid(CHOCPILOT_F("boolean expected"));
  out = *v == 't';
  return ok();
}

// --- pisanie JSON ---

class Writer {
 public:
  Writer(char* buf, size_t cap) : buf_(buf), cap_(cap) {}

  void put(char c) {
    if (len_ + 1 < cap_) {
      buf_[len_++] = c;
    } else {
      full_ = true;
    }
  }

  // Fragment JSON z pamięci programu, bez zmian.
  void raw(const char* pgm) {
    for (char c; (c = static_cast<char>(pgmByte(pgm))) != '\0'; ++pgm) put(c);
  }

  // Napis w cudzysłowie, ze znakami ucieczki; progmem = źródło w pamięci programu.
  void quoted(const char* s, bool progmem) {
    put('"');
    for (;; ++s) {
      const char c = progmem ? static_cast<char>(pgmByte(s)) : *s;
      if (c == '\0') break;
      if (c == '"' || c == '\\') {
        put('\\');
        put(c);
      } else if (c == '\n') {
        raw(CHOCPILOT_P("\\n"));
      } else if (c == '\r') {
        raw(CHOCPILOT_P("\\r"));
      } else if (c == '\t') {
        raw(CHOCPILOT_P("\\t"));
      } else if (static_cast<uint8_t>(c) < 0x20) {
        const uint8_t low = static_cast<uint8_t>(c & 0x0F);
        raw(CHOCPILOT_P("\\u00"));
        put(static_cast<char>('0' + (c >> 4)));
        put(static_cast<char>(low < 10 ? '0' + low : 'a' + low - 10));
      } else {
        put(c);
      }
    }
    put('"');
  }

  void quotedP(FlashText s) { quoted(flashChars(s), true); }

  void number(uint32_t value) {
    char digits[10];
    uint8_t n = 0;
    do {
      digits[n++] = static_cast<char>('0' + value % 10);
      value /= 10;
    } while (value != 0);
    while (n > 0) put(digits[--n]);
  }

  void number(int32_t value) {
    if (value < 0) {
      put('-');
      number(static_cast<uint32_t>(-(value + 1)) + 1u);
    } else {
      number(static_cast<uint32_t>(value));
    }
  }

  void boolean(bool value) { raw(value ? CHOCPILOT_P("true") : CHOCPILOT_P("false")); }

  // Długość wiadomości albo 0, gdy nie zmieściła się w buforze (z \0).
  size_t finish() {
    if (full_ || cap_ == 0) return 0;
    buf_[len_] = '\0';
    return len_;
  }

 private:
  char* buf_;
  size_t cap_;
  size_t len_ = 0;
  bool full_ = false;
};

}  // namespace

ParseResult parseCommand(const char* line, size_t len, Command& out) {
  // Zerowanie zamiast `out = Command()` (konstruktor to ok. 300 B kodu). Pola z niezerowymi
  // wartościami domyślnymi (flash.ms, settings.values) parser i tak ustawia przed użyciem.
  memset(static_cast<void*>(&out), 0, sizeof(out));
  gEnd = line + len;
  const char* obj = skipWs(line);
  // Jak ArduinoJson: liczy się pierwsza wartość, dalsza treść linii jest pomijana.
  if (skipValue(obj, 0) == nullptr) {
    return ParseResult{ParseStatus::BadJson, CHOCPILOT_F("invalid json")};
  }
  if (*obj != '{') return ParseResult{ParseStatus::BadJson, CHOCPILOT_F("object expected")};

  const char* type = member(obj, CHOCPILOT_P("type"));
  if (!isString(type)) return ParseResult{ParseStatus::BadJson, CHOCPILOT_F("missing type")};

  const char* id = member(obj, CHOCPILOT_P("id"));
  if (id != nullptr) {
    if (!readInt32(id, out.id)) return invalid(CHOCPILOT_F("id must be an integer"));
    out.hasId = true;
  }

  if (stringIs(type, CHOCPILOT_P("hello"))) {
    out.type = CommandType::Hello;
    return ok();
  }
  if (stringIs(type, CHOCPILOT_P("ping"))) {
    out.type = CommandType::Ping;
    return ok();
  }
  if (stringIs(type, CHOCPILOT_P("get_info"))) {
    out.type = CommandType::GetInfo;
    return ok();
  }
  if (stringIs(type, CHOCPILOT_P("display"))) {
    out.type = CommandType::Display;
    return parseDisplay(obj, out.display);
  }
  if (stringIs(type, CHOCPILOT_P("flash"))) {
    out.type = CommandType::Flash;
    return parseFlash(obj, out.flash);
  }
  if (stringIs(type, CHOCPILOT_P("settings"))) {
    out.type = CommandType::Settings;
    return parseSettings(obj, out.settings);
  }
  if (stringIs(type, CHOCPILOT_P("set_fallback"))) {
    out.type = CommandType::SetFallback;
    return parseFallback(obj, out.fallback);
  }
  if (stringIs(type, CHOCPILOT_P("reboot"))) {
    out.type = CommandType::Reboot;
    return parseFlag(obj, CHOCPILOT_P("bootloader"), false, out.flag);
  }
  if (stringIs(type, CHOCPILOT_P("test_mode"))) {
    out.type = CommandType::TestMode;
    return parseFlag(obj, CHOCPILOT_P("enable"), true, out.flag);
  }
  if (stringIs(type, CHOCPILOT_P("debug"))) {
    out.type = CommandType::Debug;
    return parseFlag(obj, CHOCPILOT_P("enable"), true, out.flag);
  }
  out.type = CommandType::Unknown;
  return ParseResult{ParseStatus::Ignored, nullptr};
}

size_t buildHello(char* buf, size_t cap, const char* board, const char* fw, bool online,
                  const I2cDiag* diag) {
  Writer w(buf, cap);
  w.raw(CHOCPILOT_P("{\"type\":\"hello\",\"device\":\"chocpilot\",\"fw\":"));
  w.quoted(fw, false);
  w.raw(CHOCPILOT_P(",\"board\":"));
  w.quoted(board, false);
  w.raw(CHOCPILOT_P(",\"keys\":"));
  w.number(static_cast<uint32_t>(kTotalKeys));
  w.raw(CHOCPILOT_P(",\"encoder\":true,\"hid\":true,\"online\":"));
  w.boolean(online);
  if (diag != nullptr) {
    w.raw(CHOCPILOT_P(",\"oled\":"));
    if (diag->oledAddr != 0) {
      w.number(static_cast<uint32_t>(diag->oledAddr));
    } else {
      w.raw(CHOCPILOT_P("null"));  // ekran nie odpowiada
    }
    w.raw(CHOCPILOT_P(",\"i2c\":["));
    for (uint8_t i = 0; i < diag->count && i < sizeof(diag->devices); ++i) {
      if (i > 0) w.put(',');
      w.number(static_cast<uint32_t>(diag->devices[i]));
    }
    w.put(']');
    if (diag->sdaLevel >= 0 && diag->sclLevel >= 0) {
      w.raw(CHOCPILOT_P(",\"lines\":{\"sda\":"));
      w.number(static_cast<int32_t>(diag->sdaLevel));
      w.raw(CHOCPILOT_P(",\"scl\":"));
      w.number(static_cast<int32_t>(diag->sclLevel));
      w.put('}');
    }
    if (diag->swapped) w.raw(CHOCPILOT_P(",\"swapped\":true"));
  }
  w.raw(CHOCPILOT_P(",\"max_line\":"));
  w.number(static_cast<uint32_t>(kMaxLineLength));
  w.put('}');
  return w.finish();
}

size_t buildKey(char* buf, size_t cap, uint8_t key, bool down, uint32_t t) {
  Writer w(buf, cap);
  w.raw(CHOCPILOT_P("{\"type\":\"key\",\"key\":"));
  w.number(static_cast<uint32_t>(key));
  w.raw(down ? CHOCPILOT_P(",\"action\":\"down\",\"t\":") : CHOCPILOT_P(",\"action\":\"up\",\"t\":"));
  w.number(t);
  w.put('}');
  return w.finish();
}

size_t buildEnc(char* buf, size_t cap, int32_t steps, uint32_t t) {
  Writer w(buf, cap);
  w.raw(CHOCPILOT_P("{\"type\":\"enc\",\"steps\":"));
  w.number(steps);
  w.raw(CHOCPILOT_P(",\"t\":"));
  w.number(t);
  w.put('}');
  return w.finish();
}

size_t buildAck(char* buf, size_t cap, int32_t id) {
  Writer w(buf, cap);
  w.raw(CHOCPILOT_P("{\"type\":\"ack\",\"id\":"));
  w.number(id);
  w.put('}');
  return w.finish();
}

size_t buildError(char* buf, size_t cap, bool hasId, int32_t id, FlashText msg) {
  Writer w(buf, cap);
  w.raw(CHOCPILOT_P("{\"type\":\"error\","));
  if (hasId) {
    w.raw(CHOCPILOT_P("\"id\":"));
    w.number(id);
    w.put(',');
  }
  w.raw(CHOCPILOT_P("\"msg\":"));
  w.quotedP(msg);
  w.put('}');
  return w.finish();
}

size_t buildLog(char* buf, size_t cap, FlashText level, FlashText msg) {
  Writer w(buf, cap);
  w.raw(CHOCPILOT_P("{\"type\":\"log\",\"level\":"));
  w.quotedP(level);
  w.raw(CHOCPILOT_P(",\"msg\":"));
  w.quotedP(msg);
  w.put('}');
  return w.finish();
}

size_t buildTest(char* buf, size_t cap, bool active) {
  Writer w(buf, cap);
  w.raw(CHOCPILOT_P("{\"type\":\"test\",\"active\":"));
  w.boolean(active);
  w.put('}');
  return w.finish();
}

}  // namespace chocpilot

#endif  // CHOCPILOT_COMPACT
