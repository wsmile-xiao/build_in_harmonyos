#include <botan/hash.h>

#include <cstddef>
#include <iostream>
#include <string>

static std::string to_hex_lower(const Botan::secure_vector<uint8_t> &bytes)
{
    static const char hex[] = "0123456789abcdef";
    std::string out;
    out.reserve(bytes.size() * 2);
    for (auto b : bytes)
    {
        out.push_back(hex[(b >> 4) & 0xF]);
        out.push_back(hex[b & 0xF]);
    }
    return out;
}

int main()
{
    auto hash = Botan::HashFunction::create("SHA-256");
    if (!hash)
        return 1;
    const std::string payload = "OpenHarmony Botan";
    hash->update(payload);
    const auto digest_raw = hash->final();
    const std::string digest = to_hex_lower(digest_raw);
    const std::string expected =
        "c7c738acb29ccbdbb549e51733d6969b7da58b6783a9354b39ba5f2d7fd23d6c";
    if (digest != expected)
    {
        std::cerr << digest << std::endl;
        return 2;
    }
    return 0;
}
