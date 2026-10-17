// test_package.cpp — Substantive consumer test for cppcodec (Conan L1)
// Verifies base64, base64url, base32 and hex encode/decode round-trips
// through the packaged header-only API.

#include <cppcodec/base64_rfc4648.hpp>
#include <cppcodec/base64_url.hpp>
#include <cppcodec/base32_rfc4648.hpp>
#include <cppcodec/hex_lower.hpp>
#include <string>
#include <vector>
#include <cstdio>
#include <cstring>
#include <cstdlib>

static int failures = 0;
#define CHECK(cond, label) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", label); failures++; } \
} while (0)

int main() {
    const std::string input("Hello, cppcodec!");
    const unsigned char *raw =
        reinterpret_cast<const unsigned char *>(input.data());
    const size_t len = input.size();

    // base64 (RFC 4648)
    std::string b64 = cppcodec::base64_rfc4648::encode(raw, len);
    std::vector<unsigned char> b64dec = cppcodec::base64_rfc4648::decode(b64);
    CHECK(b64 != "Hello, cppcodec!", "base64 encode changed content");
    CHECK(std::string(b64dec.begin(), b64dec.end()) == input,
          "base64 round-trip");

    // base64url
    std::string b64u = cppcodec::base64_url::encode(raw, len);
    std::vector<unsigned char> b64udec = cppcodec::base64_url::decode(b64u);
    CHECK(std::string(b64udec.begin(), b64udec.end()) == input,
          "base64url round-trip");

    // base32 (RFC 4648)
    std::string b32 = cppcodec::base32_rfc4648::encode(raw, len);
    std::vector<unsigned char> b32dec = cppcodec::base32_rfc4648::decode(b32);
    CHECK(std::string(b32dec.begin(), b32dec.end()) == input,
          "base32 round-trip");

    // hex (lower)
    std::string hex = cppcodec::hex_lower::encode(raw, len);
    std::vector<unsigned char> hexdec = cppcodec::hex_lower::decode(hex);
    CHECK(std::string(hexdec.begin(), hexdec.end()) == input,
          "hex round-trip");

    if (failures == 0) {
        printf("PASS: cppcodec header-only consumer test OK\n");
        return 0;
    }
    printf("FAILED: %d check(s) failed\n", failures);
    return 1;
}