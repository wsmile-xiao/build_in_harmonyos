// Consumer test for tsduck/4676 - Conan L1 test (real API calls, R34).
//
// Each check prints exactly one "CHECK-OK: <name>" line on success; the
// test_package conanfile counts those lines for HMBS_TEST_PACKAGE_RESULT
// (exit-0-alone is not proof). Uses the generated master header "tsduck.h"
// like upstream sample apps (sample/sample-app/myexec.cpp), plus the
// TS_VERSION_* macros from transition (3.44-4676).
//
// Checks (6):
//   1. version-macros  - TS_VERSION_MAJOR/MINOR/COMMIT == 3/44/4676
//   2. packet-init     - ts::TSPacket::init() gives a valid sync byte
//   3. null-pid        - fresh init() packet has PID ts::PID_NULL (0x1FFF)
//   4. set-pid         - setPID/getPID round-trip preserves 13-bit PID
//   5. cc-zero         - fresh init() packet continuity counter is 0
//   6. ustring-upper   - ts::UString narrow-string ctor + convertToUpper

#include "tsduck.h"

#include <cstdint>
#include <cstdio>

static int failures = 0;

#define CHECK(name, cond)                                             \
    do {                                                              \
        if (cond) {                                                   \
            std::printf("CHECK-OK: %s\n", name);                      \
        }                                                             \
        else {                                                        \
            std::printf("CHECK-FAIL: %s (%s:%d)\n", name, __FILE__, __LINE__); \
            ++failures;                                               \
        }                                                             \
    } while (false)

int main()
{
    // 1. Version macros match the adapted upstream tag v3.44-4676.
    CHECK("version-macros",
          TS_VERSION_MAJOR == 3 && TS_VERSION_MINOR == 44 && TS_COMMIT == 4676);

    // 2-5. TS packet lifecycle through the real libtsduck API.
    ts::TSPacket pkt;
    pkt.init();  // default: null packet, cc 0, 0xFF payload
    CHECK("packet-init", pkt.hasValidSync());
    CHECK("null-pid", pkt.getPID() == ts::PID_NULL);
    pkt.setPID(0x1A2B);
    CHECK("set-pid", pkt.getPID() == 0x1A2B);
    ts::TSPacket fresh;
    fresh.init(ts::PID_NULL, 0);
    CHECK("cc-zero", fresh.getCC() == 0);

    // 6. Unicode string class: narrow-string construction + case mapping.
    ts::UString text("tsduck");
    CHECK("ustring-upper",
          text.size() == 6 && (text.convertToUpper(), text == ts::UString("TSDUCK")));

    if (failures == 0) {
        std::printf("ALL CHECKS PASSED\n");
        return 0;
    }
    std::printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
