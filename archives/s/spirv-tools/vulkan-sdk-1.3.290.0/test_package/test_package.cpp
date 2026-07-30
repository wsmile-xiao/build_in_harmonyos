#include <spirv-tools/libspirv.hpp>

int main() {
    spvtools::SpirvTools tools(SPV_ENV_UNIVERSAL_1_5);
    return tools.IsValid() ? 0 : 1;
}
