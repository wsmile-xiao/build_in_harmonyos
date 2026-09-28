// Consumer test for libapogee3.
//
// The library is a hardware camera driver: its public entry points (ApogeeCam,
// GenOne, Alta/Aspen I/O) all require a live USB or Ethernet camera. The
// CamModel namespace, however, is a set of pure functions that decode platform
// and firmware metadata from IDs / strings with NO hardware, USB, network, or
// config-file access. These assertions exercise the installed headers and the
// shared library's exported symbols end to end (link + run), which is the part
// the OHOS adaptation changes.
#include "CameraInfo.h"

#include <cstdio>
#include <stdexcept>
#include <string>

static int g_checks = 0;
static int g_failures = 0;

static void check(bool condition, const char *message) {
  ++g_checks;
  if (!condition) {
    ++g_failures;
    std::fprintf(stderr, "FAIL: %s\n", message);
  }
}

int main() {
  using namespace CamModel;

  // --- GetPlatformType(std::string): pure prefix lookup, no I/O. ---
  check(GetPlatformType("AltaU") == ALTAU, "platform AltaU");
  check(GetPlatformType("AltaE") == ALTAE, "platform AltaE");
  check(GetPlatformType("Ascent") == ASCENT, "platform Ascent");
  check(GetPlatformType("Aspen") == ASPEN, "platform Aspen");
  check(GetPlatformType("HiC") == HIC, "platform HiC");
  check(GetPlatformType("AltaF") == ALTAF, "platform AltaF");
  check(GetPlatformType("Quad") == QUAD, "platform Quad");
  check(GetPlatformType("Unknown") == UNKNOWN_PLATFORM, "platform unknown");

  // --- GetPlatformStr(412): hardcoded PMO_ID short-circuits to "Quad" ---
  // without touching the camera config file.
  check(GetPlatformStr(412) == "Quad", "GetPlatformStr(412) == Quad");
  check(GetPlatformType(412) == QUAD, "GetPlatformType(412) == QUAD");

  // --- Firmware-revision classification (pure integer ranges). ---
  // Alta: 0 < rev < MAX_ALTA_FIRMWARE_REV (0x0064)
  check(IsAlta(0x0040) == true, "IsAlta(0x0040) true");
  check(IsAlta(0x0000) == false, "IsAlta(0) false");
  check(IsAlta(0x0064) == false, "IsAlta(0x0064) false (upper bound)");
  // Gen2: MIN_GEN2_FIRMWARE (0x0064) <= rev <= MAX_GEN2_FIRMWARE (0x0400)
  check(IsGen2Platform(0x0064) == true, "IsGen2Platform(0x0064) true (lower)");
  check(IsGen2Platform(0x0400) == true, "IsGen2Platform(0x0400) true (upper)");
  check(IsGen2Platform(0x0401) == false, "IsGen2Platform(0x0401) false");
  // Good when exactly one of Alta/Gen2 matches.
  check(IsFirmwareRevGood(0x0040) == true, "rev good (alta only)");
  check(IsFirmwareRevGood(0x0200) == true, "rev good (gen2 only)");
  check(IsFirmwareRevGood(0x0000) == false, "rev bad (neither)");
  check(IsFirmwareRevGood(0x0064) == true, "rev good (boundary, gen2)");

  // --- MaskRawId: applies the Alta/Gen2 camera-id mask. ---
  check(MaskRawId(0x0040, 0x064) == (0x064 & ALTA_CAMERA_ID_MASK),
        "MaskRawId alta mask");
  check(MaskRawId(0x0200, 0x164) == (0x164 & GEN2_CAMERA_ID_MASK),
        "MaskRawId gen2 mask");
  // A firmware revision that matches neither platform is rejected.
  bool threw = false;
  try {
    MaskRawId(0x0000, 0x064);
  } catch (const std::runtime_error &) {
    threw = true;
  }
  check(threw, "MaskRawId rejects bad firmware revision");

  // --- GetNoOpFirmwareRev: hex rendering of NO_OP_FRMWR_REV (0x0). ---
  check(GetNoOpFirmwareRev() == "0", "GetNoOpFirmwareRev() == \"0\"");

  std::printf("libapogee3 consumer: %d checks, %d failures\n", g_checks,
              g_failures);
  return g_failures == 0 ? 0 : 1;
}
