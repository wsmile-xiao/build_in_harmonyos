#include <ktx.h>
#include <stdio.h>

int main(void) {
    ktxTexture* texture = NULL;
    /* Call the real libktx API: create texture from empty memory.
     * This should fail since 0-size data is invalid. */
    KTX_error_code result = ktxTexture_CreateFromMemory(
        (const ktx_uint8_t*)"", 0,
        KTX_TEXTURE_CREATE_NO_FLAGS,
        &texture);
    if (result == KTX_SUCCESS) {
        if (texture) ktxTexture_Destroy(texture);
        fprintf(stderr, "FAIL: unexpected success with empty data\n");
        return 1;
    }
    printf("OK: ktx API call returned error code %d (expected non-success)\n", result);
    return 0;
}
