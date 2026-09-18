/* HarmonyOS-specific validation test for exr_image 0.1.0-rc3.
 *
 * Unlike the upstream tests (which hardcode writable /tmp paths that do not
 * exist on the OHOS device), this test exercises the memory-based public ABI:
 *   - multipart write (two parts) -> exri_writef_multipart_to_memory
 *   - part count / part info readback
 *   - negative detection (non-EXR bytes rejected by exri_is_exr_from_memory)
 *   - tiled write + tiled level count + tiled level load (memory versions)
 *   - deep-part discrimination (non-deep image correctly rejected as not deep)
 * All checks run with no filesystem writes, matching the OHOS read-only /tmp.
 */
#define EXR_IMAGE_IMPLEMENTATION
#include <exr_image.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail_count = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            fprintf(stderr, "FAIL: %s (%s)\n", msg, exri_failure_reason()); \
            fail_count++;                                                   \
        } else {                                                            \
            printf("PASS: %s\n", msg);                                      \
        }                                                                   \
    } while (0)

int main(void)
{
    static float pixels_a[2 * 2 * 4] = {
        1.0f, 0.0f, 0.0f, 1.0f,
        0.0f, 1.0f, 0.0f, 1.0f,
        0.0f, 0.0f, 1.0f, 1.0f,
        2.0f, 3.0f, 4.0f, 1.0f
    };
    static float pixels_b[1 * 1 * 4] = { 0.5f, 0.25f, 0.125f, 1.0f };
    static float single[2 * 2 * 4] = {
        1.0f, 1.0f, 1.0f, 1.0f,
        1.0f, 1.0f, 1.0f, 1.0f,
        1.0f, 1.0f, 1.0f, 1.0f,
        1.0f, 1.0f, 1.0f, 1.0f
    };
    exri_write_options options;
    exri_write_part parts[2];
    exri_uc *encoded = NULL;
    size_t encoded_len = 0;
    int num_parts = 0;
    int x = 0, y = 0, comp = 0;
    int num_channels = 0, total_samples = 0;
    int nx = 0, ny = 0;
    static unsigned char not_exr[8] = { 0x89u, 'P', 'N', 'G', 13u, 10u, 26u, 10u };
    int version = 0, flags = 0;

    options.compression = EXRI_WRITE_COMPRESSION_ZIP;
    options.pixel_type = EXRI_WRITE_PIXEL_FLOAT;
    options.tiled = 0;
    options.tile_size = 0;
    options.level_mode = EXRI_WRITE_LEVEL_ONE;
    options.level_rounding = EXRI_WRITE_ROUND_DOWN;

    /* multipart write: two parts */
    memset(parts, 0, sizeof(parts));
    parts[0].name = "main";
    parts[0].width = 2;
    parts[0].height = 2;
    parts[0].num_channels = 4;
    parts[0].data = pixels_a;
    parts[0].options = options;
    parts[1].name = "depth";
    parts[1].width = 1;
    parts[1].height = 1;
    parts[1].num_channels = 4;
    parts[1].data = pixels_b;
    parts[1].options = options;

    CHECK(exri_writef_multipart_to_memory(&encoded, &encoded_len, parts, 2),
          "multipart_to_memory write");
    CHECK(encoded != NULL && encoded_len > 0, "multipart produced data");

    CHECK(exri_is_exr_from_memory(encoded, encoded_len), "is_exr_from_memory");
    CHECK(!exri_is_exr_from_memory(not_exr, sizeof(not_exr)), "negative: PNG not EXR");
    CHECK(exri_version_from_memory(encoded, encoded_len, &version, &flags),
          "version_from_memory");

    CHECK(exri_part_count_from_memory(encoded, encoded_len, &num_parts), "part_count");
    CHECK(num_parts == 2, "two parts detected");
    CHECK(exri_part_info_from_memory(encoded, encoded_len, 0, &x, &y, &comp),
          "part[0] info");
    CHECK(x == 2 && y == 2 && comp == 4, "part[0] 2x2x4");
    CHECK(exri_part_info_from_memory(encoded, encoded_len, 1, &x, &y, &comp),
          "part[1] info");
    CHECK(x == 1 && y == 1, "part[1] 1x1");

    /* tiled: direct single-part tiled write (mipmap levels), then query +
     * load a level through the memory ABI. */
    {
        exri_write_options tiled_opts;
        exri_uc *mem2 = NULL;
        size_t len2 = 0;

        tiled_opts = options;
        tiled_opts.tiled = 1;
        tiled_opts.tile_size = 1;
        tiled_opts.level_mode = EXRI_WRITE_LEVEL_MIPMAP;
        CHECK(exri_writef_to_memory(&mem2, &len2, 2, 2, 4, single, &tiled_opts),
              "tiled write (direct)");
        CHECK(mem2 != NULL && len2 > 0, "tiled produced data");
        if (mem2 != NULL) {
            CHECK(exri_part_tiled_level_count_from_memory(mem2, len2, 0, &nx, &ny),
                  "tiled level count");
            CHECK(nx >= 1 && ny >= 1, "tiled levels present");
            {
                float *px = NULL;
                CHECK(exri_loadf_tiled_level_from_memory(&px, mem2, len2, 0, 0,
                                                         &x, &y, &comp, 4,
                                                         EXRI_LOAD_DEFAULT),
                      "tiled level load");
                if (px != NULL) {
                    CHECK(x == 2 && y == 2, "tiled load dims");
                    exri_image_free(px);
                }
            }
            free(mem2);
        }
    }

    /* deep-part discrimination on a non-deep image: must be rejected, proving
     * the library does not mis-report deep parts on scanline data. */
    num_channels = total_samples = 0;
    CHECK(!exri_deep_part_info_from_memory(encoded, encoded_len, 0, &x, &y,
                                           &num_channels, &total_samples),
          "deep_part_info rejected on scanline image");

    if (encoded != NULL)
        free(encoded);

    if (fail_count == 0) {
        printf("ALL OHOS-SPECIFIC CHECKS PASSED\n");
        return 0;
    }
    fprintf(stderr, "%d OHOS-SPECIFIC CHECK(S) FAILED\n", fail_count);
    return 1;
}
