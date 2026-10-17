#include <stdint.h>
#include <stdio.h>

#include <spirv/unified1/spirv.h>

int main(void) {
    const uint32_t module_header[] = {
        SpvMagicNumber,
        SpvVersion,
        0,
        1,
        0,
    };

    if (module_header[0] != 0x07230203u || module_header[1] == 0u || SpvOpNop != 0) {
        fprintf(stderr, "SPIR-V public constants are invalid\n");
        return 1;
    }

    printf("SPIRV-Headers: magic=0x%08x version=0x%08x op_nop=%d\n",
           module_header[0], module_header[1], SpvOpNop);
    return 0;
}
