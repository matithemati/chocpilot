#include "settings.h"

#include "config.h"
#include "hal/hal.h"
#include "time_util.h"

namespace chocpilot {

namespace {
#if defined(CHOCPILOT_COMPACT)
// Mało RAM: bufor zapisu (ok. 170 B) tylko na stosie na czas wczytania / zapisu.
#define CHOCPILOT_CONFIG_BUFFER char gBuffer[kConfigBufSize]
#else
char gBuffer[kConfigBufSize];
#define CHOCPILOT_CONFIG_BUFFER
#endif
}  // namespace

bool ConfigStore::load(DeviceConfig& cfg) {
  CHOCPILOT_CONFIG_BUFFER;
  cfg.setDefaults();
  if (!hal::storageBegin()) return false;
  const size_t n = hal::storageLoad(gBuffer, sizeof(gBuffer));
  if (n == 0) return false;
  return decodeConfig(gBuffer, n, cfg);
}

void ConfigStore::markDirty(uint32_t nowMs) {
  dirty_ = true;
  dirtySince_ = nowMs;
}

bool ConfigStore::update(const DeviceConfig& cfg, uint32_t nowMs) {
  if (!dirty_ || !elapsed(nowMs, dirtySince_, kConfigSaveDelayMs)) return false;
  return flush(cfg);
}

bool ConfigStore::flush(const DeviceConfig& cfg) {
  if (!dirty_) return true;
  dirty_ = false;
  CHOCPILOT_CONFIG_BUFFER;
  const size_t n = encodeConfig(cfg, gBuffer, sizeof(gBuffer));
  if (n == 0) return false;
  return hal::storageSave(gBuffer, n);
}

}  // namespace chocpilot
