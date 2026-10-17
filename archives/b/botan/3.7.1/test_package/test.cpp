#include <botan/version.h>
#include <botan/hex.h>
#include <botan/hash.h>
#include <botan/mac.h>
#include <botan/auto_rng.h>
#include <iostream>
#include <string>
#include <vector>

int main() {
    int failures = 0;

    // 1. version identity check (must be 3.7.1)
    const uint32_t major = Botan::version_major();
    const uint32_t minor = Botan::version_minor();
    const uint32_t patch = Botan::version_patch();
    std::cout << "botan version: " << Botan::version_string() << std::endl;
    if(major != 3 || minor != 7 || patch != 1) {
        std::cerr << "FAIL: unexpected version " << major << "." << minor << "." << patch << std::endl;
        failures++;
    }

    // 2. SHA-256 known-answer test (FIPS 180-2 vector: hash of "abc")
    auto sha256 = Botan::HashFunction::create_or_throw("SHA-256");
    sha256->update(std::string("abc"));
    const std::string digest = Botan::hex_encode(sha256->final());
    const std::string expected = "BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD";
    std::cout << "sha256(abc) = " << digest << std::endl;
    if(digest != expected) {
        std::cerr << "FAIL: sha256 mismatch, expected " << expected << std::endl;
        failures++;
    }

    // 3. HMAC-SHA-256 KAT (RFC 4231 test case 2) — via public MAC factory
    const std::vector<uint8_t> key{'J', 'e', 'f', 'e'};
    const std::string data = "what do ya want for nothing?";
    auto hmac = Botan::MessageAuthenticationCode::create_or_throw("HMAC(SHA-256)");
    hmac->set_key(key);
    hmac->update(data);
    const std::string mac = Botan::hex_encode(hmac->final());
    const std::string expected_mac = "5BDCC146BF60754E6A042426089575C75A003F089D2739839DEC58B964EC3843";
    std::cout << "hmac-sha256 = " << mac << std::endl;
    if(mac != expected_mac) {
        std::cerr << "FAIL: hmac mismatch, expected " << expected_mac << std::endl;
        failures++;
    }

    // 4. AutoSeeded_RNG round-trip
    Botan::AutoSeeded_RNG rng;
    const auto nonce = rng.random_vec(16);
    if(nonce.size() != 16) {
        std::cerr << "FAIL: rng produced wrong size" << std::endl;
        failures++;
    }

    if(failures == 0) {
        std::cout << "ALL CHECKS PASSED" << std::endl;
        return 0;
    }
    return 1;
}
