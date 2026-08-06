#include <ffnvcodec/nvEncodeAPI.h>
#include <stdio.h>

int main(void) {
    /* Verify NVENC API header is correctly installed and usable */
    NVENCSTATUS status = NV_ENC_SUCCESS;
    if (status != 0) {
        fprintf(stderr, "FAIL: NV_ENC_SUCCESS is not 0 (got %d)\n", (int)status);
        return 1;
    }
    printf("OK: ffnvcodec-headers 13.0.19.0 — NV_ENC_SUCCESS=%d\n", (int)status);
    return 0;
}
