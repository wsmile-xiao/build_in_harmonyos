/* exr_image is a single-header library: per upstream README, the implementation
 * macro must be defined in exactly one translation unit, then the header is
 * included normally everywhere else. The consumer test below is that one TU. */
#define EXR_IMAGE_IMPLEMENTATION
#include <exr_image.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* HarmonyOS consumer test for exr_image (single-header C89 library).
 *
 * Exercises the public memory-based ABI only (no filesystem dependency):
 *   1. exri_writef_to_memory  - encode a small RGBA image as OpenEXR
 *   2. exri_is_exr_from_memory - verify the magic/version header
 *   3. exri_info_from_memory   - read back dimensions and channel count
 *   4. exri_loadf_from_memory  - decode pixels back
 *   5. exri_image_free         - release the decoded buffer
 *   6. exri_failure_reason     - diagnostic on failure
 */
int main(void)
{
    static float pixels[2 * 2 * 4] = {
        1.0f, 0.0f, 0.0f, 1.0f,
        0.0f, 1.0f, 0.0f, 1.0f,
        0.0f, 0.0f, 1.0f, 1.0f,
        2.0f, 3.0f, 4.0f, 1.0f
    };
    exri_write_options options;
    exri_uc *encoded = NULL;
    size_t encoded_len = 0;
    float *decoded = NULL;
    int x = 0, y = 0, comp = 0;
    int version = 0, flags = 0;
    int ok = 0;

    options.compression = EXRI_WRITE_COMPRESSION_ZIP;
    options.pixel_type = EXRI_WRITE_PIXEL_FLOAT;
    options.tiled = 0;
    options.tile_size = 0;
    options.level_mode = EXRI_WRITE_LEVEL_ONE;
    options.level_rounding = EXRI_WRITE_ROUND_DOWN;

    if (!exri_writef_to_memory(&encoded, &encoded_len, 2, 2, 4,
                               pixels, &options)) {
        fprintf(stderr, "writef_to_memory failed: %s\n", exri_failure_reason());
        return 1;
    }
    if (encoded == NULL || encoded_len == 0) {
        fprintf(stderr, "writef_to_memory produced no data\n");
        return 1;
    }

    if (!exri_is_exr_from_memory(encoded, encoded_len)) {
        fprintf(stderr, "is_exr_from_memory: expected EXR: %s\n", exri_failure_reason());
        goto done;
    }

    if (!exri_version_from_memory(encoded, encoded_len, &version, &flags)) {
        fprintf(stderr, "version_from_memory failed: %s\n", exri_failure_reason());
        goto done;
    }

    if (!exri_info_from_memory(encoded, encoded_len, &x, &y, &comp)) {
        fprintf(stderr, "info_from_memory failed: %s\n", exri_failure_reason());
        goto done;
    }
    if (x != 2 || y != 2 || comp != 4) {
        fprintf(stderr, "info mismatch: got %dx%d channels=%d\n", x, y, comp);
        goto done;
    }

    decoded = NULL;
    if (!exri_loadf_from_memory(&decoded, encoded, encoded_len,
                                &x, &y, &comp, 4, EXRI_LOAD_DEFAULT)) {
        fprintf(stderr, "loadf_from_memory failed: %s\n", exri_failure_reason());
        goto done;
    }
    if (decoded == NULL || x != 2 || y != 2 || comp != 4) {
        fprintf(stderr, "load dims mismatch: %dx%d channels=%d\n", x, y, comp);
        goto done;
    }
    if (decoded[0] != 1.0f || decoded[1] != 0.0f || decoded[5] != 1.0f) {
        fprintf(stderr, "pixel data mismatch: %f %f %f\n", decoded[0], decoded[1], decoded[5]);
        goto done;
    }

    ok = 1;
    printf("exr_image consumer test OK: wrote %zu bytes, version=%d, loaded %dx%d channels=%d\n",
           encoded_len, version, x, y, comp);

done:
    if (decoded != NULL)
        exri_image_free(decoded);
    if (encoded != NULL)
        free(encoded);
    return ok ? 0 : 1;
}
