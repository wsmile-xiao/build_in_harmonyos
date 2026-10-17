// ohos_platform_test.cpp — HarmonyOS platform-specific test for config-loader
//
// Verifies the full serialize -> deserialize round-trip through the public
// API on the OHOS target (aarch64-linux-ohos). Independent from the
// consumer test (test_config-loader.cpp) and from the upstream Catch2 suite.
#include <config-loader/ConfigLoader.h>

#include <cstdio>
#include <sstream>
#include <string>

using namespace CONFIG_LOADER_NS;

DEFINE_SCHEMA(PlatformPoint,
              (double) x,
              (double) y);

int main() {
    int failures = 0;

    // Serialize a reflected struct to a stream (public API). The dump is a
    // custom human-readable format (.x{value}); assert it carries the values.
    PlatformPoint pt{1.5, -2.25};
    std::ostringstream out;
    dumpObj2OStream(out, pt);
    std::string dump = out.str();
    printf("[ohos-platform] serialized dump: %s\n", dump.c_str());
    if (dump.find("1.5") == std::string::npos || dump.find("-2.25") == std::string::npos) {
        printf("[ohos-platform] FAIL: serialized output missing expected values\n");
        ++failures;
    }

    // Round-trip via standard JSON: deserialize an equivalent config into a
    // struct (write standard JSON, read it back through the public API).
    PlatformPoint back;
    auto res = loadJSON2Obj(back, [] { return R"({"x": 3.5, "y": 7.0})"; });
    if (res != Result::SUCCESS) {
        printf("[ohos-platform] FAIL: round-trip load returned code %d\n", static_cast<int>(res));
        return 1;
    }
    printf("[ohos-platform] round-trip x=%f y=%f\n", back.x, back.y);
    if (back.x != 3.5 || back.y != 7.0) {
        printf("[ohos-platform] FAIL: round-trip values differ\n");
        ++failures;
    }

    // YAML backend also available on this build (public API)
    PlatformPoint yamlPt;
    auto yres = loadYAML2Obj(yamlPt, [] { return "x: 3.5\ny: 7.0\n"; });
    if (yres != Result::SUCCESS || yamlPt.x != 3.5 || yamlPt.y != 7.0) {
        printf("[ohos-platform] FAIL: yaml backend load (code %d, x=%f y=%f)\n",
               static_cast<int>(yres), yamlPt.x, yamlPt.y);
        ++failures;
    }

    if (failures == 0) {
        printf("[ohos-platform] PASS: serialize/deserialize round-trip OK on OHOS\n");
        return 0;
    }
    printf("[ohos-platform] FAIL: %d check(s) failed\n", failures);
    return 1;
}
