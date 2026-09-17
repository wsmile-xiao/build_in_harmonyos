#include <botan/hash.h>
#include <botan/hex.h>

#include <cstddef>
#include <iostream>
#include <string>

int main()
{
    auto hash = Botan::HashFunction::create("SHA-256");
    if (!hash)
        return 1;
    const std::string payload = "OpenHarmony Botan";
    hash->update(payload);
    const std::string digest = Botan::hex_encode(hash->final(), false);
    const std::string expected =
        "c7c738acb29ccbdbb549e51733d6969b7da58b6783a9354b39ba5f2d7fd23d6c";
    if (digest != expected)
    {
        std::cerr << digest << std::endl;
        return 2;
    }

    // Round-trip assertion for the hex codec on a non-crypto path.
    const auto decoded = Botan::hex_decode("00ff10");
    if (decoded.size() != 3 || decoded[0] != 0x00 || decoded[1] != 0xff || decoded[2] != 0x10)
        return 3;
    return 0;
}
