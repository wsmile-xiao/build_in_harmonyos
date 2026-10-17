#include "SimpleIni.h"
#include <cstdio>

// R34: test_package must substantively exercise the packaged API.
// simpleini is header-only; we compile against the installed SimpleIni.h and
// verify load + set/get round-trip behaviour.
int main() {
    CSimpleIniA ini;
    // Load from an in-memory data buffer (no file system dependency).
    const char data[] = "[section]\nkey = value\n";
    SI_Error rc = ini.LoadData(data, sizeof(data) - 1);
    if (rc != SI_OK) {
        std::printf("LoadData failed: %d\n", static_cast<int>(rc));
        return 1;
    }
    const char* v = ini.GetValue("section", "key", "default");
    if (!v || std::strcmp(v, "value") != 0) {
        std::printf("GetValue mismatch: %s\n", v ? v : "(null)");
        return 1;
    }
    // Round-trip: set then read back.
    ini.SetValue("sec2", "k", "v2");
    const char* v2 = ini.GetValue("sec2", "k");
    if (!v2 || std::strcmp(v2, "v2") != 0) {
        std::printf("SetValue/GetValue round-trip failed: %s\n", v2 ? v2 : "(null)");
        return 1;
    }
    std::printf("simpleini 4.26 consumer test OK\n");
    return 0;
}
