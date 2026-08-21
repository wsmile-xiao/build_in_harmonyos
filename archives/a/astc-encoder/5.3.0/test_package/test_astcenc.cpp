/* test_package/test_astcenc.cpp — consumer test for astc-encoder 5.3.0
 *
 * Verifies:
 *   1. Config initialization succeeds for a 4x4 block
 *   2. Context allocation succeeds
 *   3. Compression + decompression round-trip completes without error
 *   4. Error string lookup works
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "astcenc.h"

static int failures = 0;

static void expect_true(int cond, const char* msg)
{
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", msg);
        failures++;
    }
}

int main(void)
{
    /* Config init: 4x4 block, LDR sRGB, FASTEST quality */
    astcenc_config config;
    astcenc_error status = astcenc_config_init(
        ASTCENC_PRF_LDR_SRGB,
        4, 4, 1,
        ASTCENC_PRE_FASTEST,
        0,  /* flags */
        &config
    );
    expect_true(status == ASTCENC_SUCCESS, "config_init succeeds");
    expect_true(
        astcenc_get_error_string(status) != nullptr,
        "error_string returns non-null for success"
    );

    /* Context alloc */
    astcenc_context* context = nullptr;
    status = astcenc_context_alloc(&config, 1, &context);
    expect_true(status == ASTCENC_SUCCESS, "context_alloc succeeds");
    if (!context) {
        fprintf(stderr, "FATAL: context is null\n");
        return 1;
    }

    /* 4x4 image, 4 channels (RGBA), filled with a gradient */
    const unsigned int dim_x = 4;
    const unsigned int dim_y = 4;
    std::vector<uint8_t> image_data(dim_x * dim_y * 4);
    for (unsigned int y = 0; y < dim_y; y++) {
        for (unsigned int x = 0; x < dim_x; x++) {
            unsigned int idx = (y * dim_x + x) * 4;
            image_data[idx + 0] = static_cast<uint8_t>(x * 64);
            image_data[idx + 1] = static_cast<uint8_t>(y * 64);
            image_data[idx + 2] = 128;
            image_data[idx + 3] = 255;
        }
    }

    astcenc_image image;
    image.dim_x = dim_x;
    image.dim_y = dim_y;
    image.dim_z = 1;
    image.data_type = ASTCENC_TYPE_U8;
    uint8_t* slices = image_data.data();
    image.data = reinterpret_cast<void**>(&slices);

    astcenc_swizzle swizzle = {
        ASTCENC_SWZ_R, ASTCENC_SWZ_G, ASTCENC_SWZ_B, ASTCENC_SWZ_A
    };

    /* One 4x4 ASTC block = 16 bytes */
    const size_t packed_size = 16;
    std::vector<uint8_t> packed(packed_size);

    status = astcenc_compress_image(
        context, &image, &swizzle,
        packed.data(), packed.size(),
        0  /* thread_index */
    );
    expect_true(status == ASTCENC_SUCCESS, "compress_image succeeds");

    /* Decompress back */
    std::vector<uint8_t> decoded(dim_x * dim_y * 4);
    uint8_t* decoded_slices = decoded.data();
    astcenc_image dec_image;
    dec_image.dim_x = dim_x;
    dec_image.dim_y = dim_y;
    dec_image.dim_z = 1;
    dec_image.data_type = ASTCENC_TYPE_U8;
    dec_image.data = reinterpret_cast<void**>(&decoded_slices);

    status = astcenc_decompress_image(
        context, packed.data(), packed.size(),
        &dec_image, &swizzle,
        0  /* thread_index */
    );
    expect_true(status == ASTCENC_SUCCESS, "decompress_image succeeds");

    astcenc_context_free(context);

    if (failures != 0) {
        fprintf(stderr, "astc-encoder test failed: %d checks\n", failures);
        return 1;
    }

    printf("astc-encoder 5.3.0 consumer test: OK\n");
    return 0;
}
