// test_package/test.cpp — consumer-perspective test for is_utf8 1.4.1
//
// Layer 2 test (see docs/TEST_QUALITY_SPEC.md): a downstream consumer
// links the packaged static library and exercises its public C API
// `bool is_utf8(const char *src, size_t len)` declared in <is_utf8.h>.
//
// Strategy (every check can really fail; see notes.md mutation evidence):
//   1. Exhaustive differential validation against an RFC 3629 reference
//      DFA for ALL 1-byte (256) and ALL 2-byte (65536) inputs  = 65792
//   2. 24 targeted sequences (valid multibyte, overlongs, surrogates,
//      truncated, high leads)
//   3. One 64 KiB mixed valid string + 2 single-byte corruptions placed
//      deep inside the SIMD main loop window (>= 16 bytes)
//   4. 1 empty-input check (len == 0, valid)
// Total: 65792 + 24 + 3 + 1 = 65820 checks (counted and printed at run time).
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "is_utf8.h"

static unsigned long long g_checks = 0;
static unsigned long long g_failures = 0;

static void check(bool cond, const char *what, size_t idx) {
  ++g_checks;
  if (!cond) {
    ++g_failures;
    std::printf("FAIL [%s] at index %zu\n", what, idx);
  }
}

// Strict RFC 3629 reference validator (independent of the tested library).
static bool ref_is_utf8(const unsigned char *s, std::size_t n) {
  std::size_t i = 0;
  while (i < n) {
    unsigned char c = s[i];
    if (c < 0x80) {
      i += 1;
      continue;
    }
    if (c < 0xC2) {
      return false; // stray continuation byte or overlong lead
    }
    if (c < 0xE0) { // 2-byte sequence
      if (i + 1 >= n) return false;
      unsigned char c2 = s[i + 1];
      if (c2 < 0x80 || c2 > 0xBF) return false;
      i += 2;
      continue;
    }
    if (c < 0xF0) { // 3-byte sequence
      if (i + 2 >= n) return false;
      unsigned char c2 = s[i + 1], c3 = s[i + 2];
      if (c == 0xE0 && c2 < 0xA0) return false; // overlong
      if (c == 0xED && c2 > 0x9F) return false; // UTF-16 surrogate
      if (c2 < 0x80 || c2 > 0xBF) return false;
      if (c3 < 0x80 || c3 > 0xBF) return false;
      i += 3;
      continue;
    }
    if (c < 0xF5) { // 4-byte sequence
      if (i + 3 >= n) return false;
      unsigned char c2 = s[i + 1], c3 = s[i + 2], c4 = s[i + 3];
      if (c == 0xF0 && c2 < 0x90) return false; // overlong
      if (c == 0xF4 && c2 > 0x8F) return false; // beyond U+10FFFF
      if (c2 < 0x80 || c2 > 0xBF) return false;
      if (c3 < 0x80 || c3 > 0xBF) return false;
      if (c4 < 0x80 || c4 > 0xBF) return false;
      i += 4;
      continue;
    }
    return false // 0xF5..0xFF are never valid leads
        ;
  }
  return true;
}

int main() {
  // 1. exhaustive differential over all 1- and 2-byte inputs (65792 checks)
  for (int b0 = 0; b0 < 256; ++b0) {
    unsigned char buf[1] = {static_cast<unsigned char>(b0)};
    bool got = is_utf8(reinterpret_cast<const char *>(buf), 1);
    bool want = ref_is_utf8(buf, 1);
    check(got == want, "diff-1byte", static_cast<size_t>(b0));
  }
  unsigned char buf2[2];
  for (int b0 = 0; b0 < 256; ++b0) {
    for (int b1 = 0; b1 < 256; ++b1) {
      buf2[0] = static_cast<unsigned char>(b0);
      buf2[1] = static_cast<unsigned char>(b1);
      bool got = is_utf8(reinterpret_cast<const char *>(buf2), 2);
      bool want = ref_is_utf8(buf2, 2);
      check(got == want, "diff-2byte", static_cast<size_t>(b0) * 256 + b1);
    }
  }

  // 2. targeted sequences (24 checks)
  struct { const char *s; bool valid; } cases[] = {
      {"", true},
      {"a", true},
      {"\x7f", true},
      {"\xc3\xa9", true},                              // U+00E9
      {"\xdf\xbf", true},                              // U+07FF
      {"\xe2\x82\xac", true},                          // U+20AC euro
      {"\xe0\xa0\x80", true},                          // U+0800 min 3-byte
      {"\xef\xbf\xbf", true},                          // U+FFFF
      {"\xf0\x90\x80\x80", true},                      // U+10000 min 4-byte
      {"\xf4\x8f\xbf\xbf", true},                      // U+10FFFF max
      {"\xf4\x90\x80\x80", false},                     // > U+10FFFF
      {"\xf5\x80\x80\x80", false},                     // lead 0xF5 invalid
      {"\xff", false},
      {"\x80", false},                                 // stray continuation
      {"\xc0\x80", false},                             // overlong NUL
      {"\xc1\xbf", false},                             // overlong
      {"\xc2", false},                                 // truncated 2-byte
      {"\xe2\x82", false},                             // truncated 3-byte
      {"\xf0\x90\x80", false},                         // truncated 4-byte
      {"\xe0\x80\x80", false},                         // overlong 3-byte
      {"\xed\xa0\x80", false},                         // surrogate U+D800
      {"\xed\xbf\xbf", false},                         // surrogate U+DFFF
      {"\xc2\x20", false},                             // bad continuation
      {"a\xed\xa0\x80z", false},                       // surrogate in context
  };
  const size_t ncases = sizeof(cases) / sizeof(cases[0]);
  for (size_t i = 0; i < ncases; ++i) {
    size_t len = std::strlen(cases[i].s);
    bool got = is_utf8(cases[i].s, len);
    check(got == cases[i].valid, "targeted", i);
  }

  // 3. long mixed string exercising the SIMD main loop (3 checks)
  std::string big;
  big.reserve(65536);
  for (size_t i = 0; i < 4096; ++i) {
    big += "a\xe2\x82\xac\xf0\x9d\x84\x9e"; // ASCII + 3-byte + 4-byte
  }
  check(is_utf8(big.data(), big.size()), "big-valid", 0);
  std::string bad_mid = big;
  bad_mid[1000] = '\xff'; // corrupt deep inside the SIMD window
  check(!is_utf8(bad_mid.data(), bad_mid.size()), "big-corrupt-0xff", 0);
  std::string bad_tail = big;
  bad_tail[2000] = '\xe2'; // dangling lead byte, following byte not a continuation
  bad_tail[2001] = 'x';
  bad_tail[2002] = 'y';
  check(!is_utf8(bad_tail.data(), bad_tail.size()), "big-corrupt-trunc", 0);

  // 4. empty input passed explicitly with len == 0 (1 check)
  check(is_utf8("", 0), "empty", 0);

  std::printf("is_utf8 test_package: assertions=%llu failures=%llu\n",
              g_checks, g_failures);
  if (g_failures != 0) {
    return EXIT_FAILURE;
  }
  std::printf("All is_utf8 consumer checks passed.\n");
  return EXIT_SUCCESS;
}
