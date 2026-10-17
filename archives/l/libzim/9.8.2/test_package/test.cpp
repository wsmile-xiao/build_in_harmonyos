#include <zim/zim.h>
#include <zim/archive.h>
#include <zim/item.h>
#include <zim/version.h>

#include <cstdio>
#include <cstring>
#include <string>

int main() {
    // Verify library loads and API is callable via getVersions()
    auto versions = zim::getVersions();
    if (versions.empty()) {
        std::fprintf(stderr, "FAIL: getVersions() returned empty\n");
        return 1;
    }

    std::printf("libzim versions:\n");
    bool found_libzim = false;
    for (const auto& v : versions) {
        std::printf("  %s: %s\n", v.first.c_str(), v.second.c_str());
        if (v.first == "libzim") {
            found_libzim = true;
        }
    }

    if (!found_libzim) {
        std::fprintf(stderr, "FAIL: libzim version not found in getVersions()\n");
        return 2;
    }

    std::printf("libzim smoke test PASSED: library loaded and getVersions() API works\n");
    return 0;
}
