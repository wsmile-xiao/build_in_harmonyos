#include <flat_hash_map.hpp>

#include <cstdint>
#include <iostream>

static_assert(sizeof(void*) == 8, "HarmonyOS PC requires a 64-bit ABI");
static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__, "HarmonyOS PC requires little endian");

int main() {
    int discovered = 0;
    int passed = 0;
#define CHECK(condition) do { ++discovered; if (condition) { ++passed; } else { std::cerr << "failed: " #condition << '\n'; } } while (false)

    ska::flat_hash_map<std::uint64_t, std::uint64_t> values;
    values.reserve(1024);
    CHECK(values.empty());
    for (std::uint64_t index = 0; index < 1024; ++index) {
        values.emplace(index, index * index);
    }
    CHECK(values.size() == 1024);
    CHECK(values.at(0) == 0);
    CHECK(values.at(1023) == 1023ULL * 1023ULL);

    std::uint64_t checksum = 0;
    for (const auto& entry : values) {
        checksum += entry.second;
    }
    CHECK(checksum == 357389824ULL);

    for (std::uint64_t index = 1; index < 1024; index += 2) {
        values.erase(index);
    }
    CHECK(values.size() == 512);
    CHECK(values.count(100) == 1);
    CHECK(values.count(101) == 0);

    const bool ok = discovered == 8 && passed == discovered;
    std::cout << "HarmonyOS aarch64 container test: " << passed << '/'
              << discovered << " passed\n";
    return ok ? 0 : 1;
}
