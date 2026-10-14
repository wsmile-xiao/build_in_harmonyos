// Consumer test for rocm-cmake 0.4.0.
//
// This translation unit is compiled twice by test_package/CMakeLists.txt:
//   * as `rocm_consumer_core` (with ROCM_CONSUMER_LIBRARY_ONLY) -> library
//   * as the `test_package` executable (without it)            -> main()
// The version values are injected by rocm_setup_version() and
// rocm_get_patch_version() at CMake configure time.
#include <cstdio>
#include <cstring>

// The version macros are injected only into the `test_package` executable
// target (see test_package/CMakeLists.txt); the `rocm_consumer_core` library
// translation unit is compiled without them. Scope the guard to the executable
// branch (`!ROCM_CONSUMER_LIBRARY_ONLY`) so the library TU does not #error.
#ifndef ROCM_CONSUMER_LIBRARY_ONLY
#ifndef ROCM_CONSUMER_VERSION
#error "ROCM_CONSUMER_VERSION must be defined by test_package/CMakeLists.txt"
#endif
#ifndef ROCM_CONSUMER_PATCH
#error "ROCM_CONSUMER_PATCH must be defined by test_package/CMakeLists.txt"
#endif
#endif  // !ROCM_CONSUMER_LIBRARY_ONLY

// Shared declarations (defined only in the library translation unit).
bool rocm_consumer_parse_version(const char *text, int &major, int &minor, int &patch);
int rocm_consumer_checksum(int major, int minor, int patch);

#ifdef ROCM_CONSUMER_LIBRARY_ONLY
bool rocm_consumer_parse_version(const char *text, int &major, int &minor, int &patch) {
    return std::sscanf(text, "%d.%d.%d", &major, &minor, &patch) == 3;
}

int rocm_consumer_checksum(int major, int minor, int patch) {
    return major * 100 + minor * 10 + patch;
}
#else
int main() {
    int major = -1, minor = -1, patch = -1;
    if (!rocm_consumer_parse_version(ROCM_CONSUMER_VERSION, major, minor, patch)) {
        std::printf("FAIL: cannot parse ROCM_CONSUMER_VERSION='%s'\n",
                    ROCM_CONSUMER_VERSION);
        return 1;
    }
    // rocm_setup_version(VERSION 0.4.0) must yield exactly 0.4.0.
    if (major != 0 || minor != 4 || patch != 0) {
        std::printf("FAIL: rocm_setup_version -> %d.%d.%d, expected 0.4.0\n",
                    major, minor, patch);
        return 2;
    }
    // rocm_get_patch_version() reads ROCM_LIBPATCH_VERSION from the environment.
    if (std::strcmp(ROCM_CONSUMER_PATCH, "0") != 0) {
        std::printf("FAIL: rocm_get_patch_version -> '%s', expected '0'\n",
                    ROCM_CONSUMER_PATCH);
        return 3;
    }
    // major * 100 + minor * 10 + patch for 0.4.0 must be 0 * 100 + 4 * 10 + 0.
    const int checksum = rocm_consumer_checksum(major, minor, patch);
    if (checksum != 40) {
        std::printf("FAIL: version checksum %d != 40\n", checksum);
        return 4;
    }
    std::printf("OK: rocm-cmake 0.4.0 consumer test passed "
                "(ROCM_VERSION=%s, PATCH=%s, checksum=%d)\n",
                ROCM_CONSUMER_VERSION, ROCM_CONSUMER_PATCH, checksum);
    return 0;
}
#endif
