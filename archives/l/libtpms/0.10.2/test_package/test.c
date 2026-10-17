#include <inttypes.h>
#include <stdio.h>

#include <libtpms/tpm_library.h>

int main(void) {
    uint32_t version = TPMLIB_GetVersion();

    if (version == 0) {
        fprintf(stderr, "TPMLIB_GetVersion returned zero\n");
        return 1;
    }

    printf("libtpms version: 0x%08" PRIx32 "\n", version);
    return 0;
}
