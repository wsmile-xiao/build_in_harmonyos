// digestpp 1.0.0 consumer test — uses only the installed public headers
// and the publicly exported digestpp::digestpp CMake target.
// Verifies real digest outputs for several public APIs (sha256, blake2b,
// sha3-512 with customizable output) against known-good values.
#include <digestpp/digestpp.hpp>
#include <cstdio>
#include <string>

static int failures = 0;

static void check(const std::string& name, const std::string& actual,
                  const std::string& expected)
{
    if (actual != expected)
    {
        std::printf("%s FAILED: expected %s, actual %s\n", name.c_str(),
                    expected.c_str(), actual.c_str());
        failures++;
    }
    else
    {
        std::printf("%s OK (%s)\n", name.c_str(), actual.c_str());
    }
}

int main()
{
    // FIPS 180-2: SHA-256("abc")
    check("sha256(abc)",
          digestpp::sha256().absorb("abc").hexdigest(),
          "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");

    // BLAKE2b-512 of the empty string
    check("blake2b512(empty)",
          digestpp::blake2b().hexdigest(),
          "786a02f742015903c6c6fd852552d272912f4740e15847618a86e217f71f5419"
          "d25e1031afee585313896444934eb04b903a685b1448b755d56f701afe9be2ce");

    // SHA3-512 of the empty string (NIST)
    check("sha3_512(empty)",
          digestpp::sha3(512).hexdigest(),
          "a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a6"
          "15b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26");

    // SHAKE256 XOF output length control — 32 hex chars == 16 bytes
    check("shake256_xof_len",
          digestpp::shake256().absorb("abc").hexsqueeze(16),
          "483366601360a8771c6863080cc4114d");

    // HMAC-style keyed BLAKE2b via public set_key API
    // (expected value cross-checked with Python hashlib.blake2b)
    check("blake2b_keyed",
          digestpp::blake2b(256).set_key(std::string(32, 0x01)).absorb("abc").hexdigest(),
          "8cc77af752046919e25cca7b87a17aaa67fb6aad75964f730a1c2178c986505c");

    if (failures == 0)
    {
        std::printf("digestpp consumer test PASSED (5 public API checks)\n");
        return 0;
    }
    std::printf("digestpp consumer test FAILED with %d errors\n", failures);
    return 1;
}