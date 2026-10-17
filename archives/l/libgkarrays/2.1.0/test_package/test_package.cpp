#include <cstdio>
#include <cstring>

#include "gkArrays.h"
#include "solArray.h"

int main() {
    int failures = 0;
    int checks = 0;

    // 1: library version is available.
    ++checks;
    char *version = gkarrays::libGkArraysVersion();
    if (version == 0 || version[0] == '\0') {
        ++failures;
        std::printf("FAIL: libGkArraysVersion returned empty\n");
    }

    // 2: version matches the packaged upstream release.
    ++checks;
    if (version == 0 || std::strcmp(version, "2.1.0") != 0) {
        ++failures;
        std::printf("FAIL: expected version 2.1.0, got %s\n", version ? version : "(null)");
    }

    // 3: short read vs theoretical length is discarded.
    ++checks;
    if (!gkarrays::gkArrays::isDiscarded(10, 20, 4)) {
        ++failures;
        std::printf("FAIL: isDiscarded(10,20,4) should be true\n");
    }

    // 4: long enough read is kept.
    ++checks;
    if (gkarrays::gkArrays::isDiscarded(30, 20, 4)) {
        ++failures;
        std::printf("FAIL: isDiscarded(30,20,4) should be false\n");
    }

    // 5: read shorter than k is discarded.
    ++checks;
    if (!gkarrays::gkArrays::isDiscarded(3, 0, 4)) {
        ++failures;
        std::printf("FAIL: isDiscarded(3,0,4) should be true\n");
    }

    // 6: SolArray set/get round-trip (core in-memory structure).
    ++checks;
    gkarrays::SolArray arr(4, 255, gkarrays::SMALL_ARRAY);
    arr.set(0, 7);
    arr.set(3, 200);
    if (arr.length() != 4 || arr.get(0) != 7 || arr.get(3) != 200) {
        ++failures;
        std::printf("FAIL: SolArray set/get round-trip mismatch\n");
    }

    if (failures == 0) {
        std::printf("libgkarrays 2.1.0 consumer: %d/%d assertions passed\n", checks, checks);
    } else {
        std::printf("libgkarrays 2.1.0 consumer: %d failures out of %d checks\n", failures, checks);
    }
    return failures == 0 ? 0 : 1;
}
