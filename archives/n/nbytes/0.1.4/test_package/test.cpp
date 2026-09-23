// Consumer test for nbytes 0.1.4.
//
// Exercises the real public API from <nbytes.h>: byte swapping (16/32/64),
// hex encoding, base64 decoding, string search, alignment helpers and ASCII
// forcing. Each check prints one "CHECK-OK: <name>" line; the test_package
// conanfile counts those lines for the HMBS_TEST_PACKAGE_RESULT
// machine-evidence marker. Exit code is 0 only if all 18 checks pass.
//
// NOTE: the assertion macro is deliberately named NBYTES_TEST_CHECK (not
// CHECK) so it can never clash with identifiers inside <nbytes.h>.
#include <cassert>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <nbytes.h>

static int g_passed = 0;

#define NBYTES_TEST_CHECK(name, expr)                             \
  do {                                                            \
    if (!(expr)) {                                                \
      std::printf("CHECK-FAIL: %s (line %d)\n", name, __LINE__);  \
      return 1;                                                   \
    }                                                             \
    std::printf("CHECK-OK: %s\n", name);                          \
    ++g_passed;                                                   \
  } while (0)

int main() {
  // 1. SwapBytes16: swap adjacent byte pairs.
  {
    std::vector<char> data = {1, 2, 3, 4, 5, 6, 7, 8};
    const std::vector<char> expected = {2, 1, 4, 3, 6, 5, 8, 7};
    NBYTES_TEST_CHECK("swap16-ret", nbytes::SwapBytes16(data.data(), data.size()));
    NBYTES_TEST_CHECK("swap16-value", data == expected);
  }
  // 2. SwapBytes32: reverse each 4-byte word.
  {
    std::vector<char> data = {1, 2, 3, 4, 5, 6, 7, 8};
    const std::vector<char> expected = {4, 3, 2, 1, 8, 7, 6, 5};
    NBYTES_TEST_CHECK("swap32-ret", nbytes::SwapBytes32(data.data(), data.size()));
    NBYTES_TEST_CHECK("swap32-value", data == expected);
  }
  // 3. SwapBytes64: reverse the full 8-byte word.
  {
    std::vector<char> data = {1, 2, 3, 4, 5, 6, 7, 8};
    const std::vector<char> expected = {8, 7, 6, 5, 4, 3, 2, 1};
    NBYTES_TEST_CHECK("swap64-ret", nbytes::SwapBytes64(data.data(), data.size()));
    NBYTES_TEST_CHECK("swap64-value", data == expected);
  }
  // 4. Misaligned size must be rejected (failure path is part of the API).
  {
    char odd[3] = {1, 2, 3};
    NBYTES_TEST_CHECK("swap16-odd-rejected", !nbytes::SwapBytes16(odd, sizeof(odd)));
    NBYTES_TEST_CHECK("swap32-odd-rejected", !nbytes::SwapBytes32(odd, sizeof(odd)));
  }
  // 5. HexEncode "Hi" -> "4869" (both overloads).
  {
    const char src[] = {'H', 'i'};
    char dst[5] = {};
    const size_t written = nbytes::HexEncode(src, 2, dst, sizeof(dst));
    NBYTES_TEST_CHECK("hex-size", written == 4);
    NBYTES_TEST_CHECK("hex-value", std::string(dst, 4) == "4869");
    NBYTES_TEST_CHECK("hex-string", nbytes::HexEncode(src, 2) == "4869");
  }
  // 6. Base64Decode "SGVsbG8=" -> "Hello".
  {
    const char* src = "SGVsbG8=";
    const size_t srclen = std::strlen(src);
    char dst[16] = {};
    const size_t decoded = nbytes::Base64Decode(dst, sizeof(dst), src, srclen);
    NBYTES_TEST_CHECK("base64-size", decoded == 5);
    NBYTES_TEST_CHECK("base64-value", std::string(dst, decoded) == "Hello");
  }
  // 7. SearchString + RoundUp helpers.
  {
    const char* haystack = "hello world";
    const size_t pos =
        nbytes::SearchString(haystack, std::strlen(haystack), "world", 5, 0, true);
    NBYTES_TEST_CHECK("search-found", pos == 6);
    const size_t missing =
        nbytes::SearchString(haystack, std::strlen(haystack), "xyz", 3, 0, true);
    NBYTES_TEST_CHECK("search-missing", missing == std::strlen(haystack));
    NBYTES_TEST_CHECK("roundup", nbytes::RoundUp<size_t>(10, 8) == 16);
  }
  // 8. ForceAscii strips the high bit; version enum lives in namespace nbytes.
  {
    const char src[] = {(char)0xC1, (char)0x42};
    char dst[2] = {};
    nbytes::ForceAscii(src, dst, sizeof(dst));
    NBYTES_TEST_CHECK("force-ascii", dst[0] == 'A' && dst[1] == 'B');
    NBYTES_TEST_CHECK("version", nbytes::NBYTES_VERSION_MAJOR == 0 &&
                                     nbytes::NBYTES_VERSION_MINOR == 1 &&
                                     nbytes::NBYTES_VERSION_REVISION == 4);
  }

  std::printf("test_nbytes: %d checks passed\n", g_passed);
  return 0;
}
