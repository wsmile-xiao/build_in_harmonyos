#include <cstdint>
#include <iostream>

#include <spirv/unified1/spirv.h>
#include <spirv/unified1/spirv.hpp>

int main() {
    int failures = 0;

    failures += SpvMagicNumber != 0x07230203u;
    failures += SpvVersion < 0x00010000u;
    failures += SpvOpNop != 0;
    failures += static_cast<std::uint32_t>(spv::OpNop) !=
                static_cast<std::uint32_t>(SpvOpNop);

    if (failures != 0) {
        std::cerr << "SPIR-V public constant validation failed: "
                  << failures << '\n';
        return 1;
    }

    std::cout << "SPIRV-Headers consumer assertions: 4/4 passed\n";
    return 0;
}
