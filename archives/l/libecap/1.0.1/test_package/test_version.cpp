/* test_version.cpp — libecap Version API + library linkage test.
 *
 * Exercises libecap::Version value semantics (known/==/!=) and calls
 * libecap::VersionString(), which is implemented in the compiled library
 * (registry.cc), proving the consumer really links against libecap.
 */
#include <cstdio>
#include <cstring>
#include <libecap/common/registry.h>
#include <libecap/common/version.h>

int main() {
    libecap::Version v(1, 0, 1);
    if (!v.known()) {
        std::printf("FAIL: Version(1,0,1) should be known\n");
        return 1;
    }
    if (v.majr != 1 || v.minr != 0 || v.micr != 1) {
        std::printf("FAIL: Version fields mismatch\n");
        return 1;
    }
    libecap::Version unknown;
    if (unknown.known()) {
        std::printf("FAIL: default Version should be unknown\n");
        return 1;
    }
    if (!(v == libecap::Version(1, 0, 1))) {
        std::printf("FAIL: Version equality broken\n");
        return 1;
    }
    if (!(v != libecap::Version(1, 0, 0))) {
        std::printf("FAIL: Version inequality broken\n");
        return 1;
    }
    const char *vs = libecap::VersionString();
    if (vs == 0 || vs[0] == '\0') {
        std::printf("FAIL: VersionString() is empty\n");
        return 1;
    }
    if (std::strstr(vs, "1.0.1") == 0) {
        std::printf("FAIL: VersionString() [%s] lacks 1.0.1\n", vs);
        return 1;
    }
    std::printf("PASS: Version API OK, linked VersionString=%s\n", vs);
    return 0;
}
