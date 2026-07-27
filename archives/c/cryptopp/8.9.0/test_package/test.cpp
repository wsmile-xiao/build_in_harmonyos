#include <cryptopp/sha.h>
#include <cryptopp/filters.h>
#include <cryptopp/hex.h>
#include <string>
#include <iostream>

int main() {
    using namespace CryptoPP;

    std::string message = "Hello, Crypto++!";
    std::string output;

    SHA256 hash;
    StringSource(message, true,
        new HashFilter(hash,
            new HexEncoder(
                new StringSink(output),
                false  // lowercase output (match sha256sum convention)
            )
        )
    );

    std::cout << "SHA256: " << output << std::endl;

    // Verify hash length (32 bytes = 64 hex chars)
    if (output.length() != 64) {
        std::cerr << "FAIL: expected 64 hex chars, got " << output.length() << std::endl;
        return 1;
    }

    // Verify actual SHA256 value (not assert, works in Release mode too)
    const std::string expected = "9009f952ce7b1d25f58c83f59f96fe23c93b57b206edb664f9162b47ac177aed";
    if (output != expected) {
        std::cerr << "FAIL: SHA256 mismatch" << std::endl;
        std::cerr << "  expected: " << expected << std::endl;
        std::cerr << "  actual:   " << output << std::endl;
        return 1;
    }

    std::cout << "Crypto++ test passed!" << std::endl;
    return 0;
}
