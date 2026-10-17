/* test_area.cpp — libecap Name + Area API test.
 *
 * Exercises libecap::Name identity semantics (unknown/known/identified,
 * image comparison) and libecap::Area buffer handling (FromTempString
 * round-trip, empty/non-empty boolean conversion).
 */
#include <cstdio>
#include <string>
#include <libecap/common/area.h>
#include <libecap/common/name.h>

int main() {
    libecap::Name unknown;
    if (unknown.known()) {
        std::printf("FAIL: default Name should be unknown\n");
        return 1;
    }
    libecap::Name method("GET");
    if (!method.known()) {
        std::printf("FAIL: Name(GET) should be known\n");
        return 1;
    }
    if (method.image() != "GET") {
        std::printf("FAIL: Name image mismatch\n");
        return 1;
    }
    if (!(method == "GET")) {
        std::printf("FAIL: Name == image broken\n");
        return 1;
    }
    libecap::Name identified("X-Custom", libecap::Name::NextId());
    if (!identified.identified()) {
        std::printf("FAIL: Name with id should be identified\n");
        return 1;
    }
    const std::string payload("hello-ecap");
    const libecap::Area area = libecap::Area::FromTempString(payload);
    if (!area) {
        std::printf("FAIL: non-empty Area should convert to true\n");
        return 1;
    }
    if (area.toString() != payload) {
        std::printf("FAIL: Area round-trip mismatch\n");
        return 1;
    }
    const libecap::Area empty;
    if (empty) {
        std::printf("FAIL: default Area should convert to false\n");
        return 1;
    }
    std::printf("PASS: Name + Area API OK\n");
    return 0;
}
