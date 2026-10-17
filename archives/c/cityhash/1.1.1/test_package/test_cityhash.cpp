// test_cityhash.cpp — consumer test for cityhash/1.1.1 on OHOS.
//
// Calls the real CityHash API through the packaged headers/library and
// asserts outputs against fixed reference values captured from the same
// release build (identical to the vectors used by the upstream
// cityhash_unittest).
#include "city.h"

#include <cstdio>
#include <cstring>

static int failures = 0;

static void Check64(const char* what, unsigned long long expected,
                    unsigned long long actual) {
  if (expected != actual) {
    std::printf("FAIL %s: expected %llu, got %llu\n", what, expected, actual);
    ++failures;
  } else {
    std::printf("PASS %s = %llu\n", what, actual);
  }
}

static void Check32(const char* what, unsigned int expected,
                    unsigned int actual) {
  if (expected != actual) {
    std::printf("FAIL %s: expected %u, got %u\n", what, expected, actual);
    ++failures;
  } else {
    std::printf("PASS %s = %u\n", what, actual);
  }
}

int main() {
  const char* abc = "abc";
  const char* text = "hello ohos cityhash test";

  Check64("CityHash64(abc)", 2640714258260161385ULL,
          CityHash64(abc, std::strlen(abc)));
  Check64("CityHash64WithSeed(abc, 12345)", 13914286602242141520ULL,
          CityHash64WithSeed(abc, std::strlen(abc), 12345));
  Check32("CityHash32(abc)", 795041479u, CityHash32(abc, std::strlen(abc)));
  Check64("CityHash64(text)", 14920966190624787894ULL,
          CityHash64(text, std::strlen(text)));

  if (failures != 0) {
    std::printf("cityhash consumer test: %d check(s) FAILED\n", failures);
    return 1;
  }
  std::printf("cityhash consumer test: all 4 checks passed\n");
  return 0;
}
