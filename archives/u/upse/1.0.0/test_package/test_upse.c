#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <upse.h>

static int assertions = 0;

static void check(int condition, const char *message)
{
    ++assertions;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(EXIT_FAILURE);
    }
}

static void test_numeric_api(void)
{
    check(fabsf(upse_strtof("12.5") - 12.5F) < 0.0001F, "positive float");
    check(fabsf(upse_strtof("-3.25") + 3.25F) < 0.0001F, "negative float");
    check(fabsf(upse_strtof("0.125") - 0.125F) < 0.0001F, "fractional float");
    check(upse_strtof("not-a-number") == 0.0F, "invalid float fallback");
}

static void test_bios_api(void)
{
    static const char path[] = "/data/storage/el2/base/cache/test-bios.bin";

    upse_set_custom_bios(NULL);
    check(upse_has_custom_bios() == 0, "BIOS initially disabled");
    check(upse_get_custom_bios() == NULL, "BIOS path initially null");
    upse_set_custom_bios(path);
    check(upse_has_custom_bios() != 0, "BIOS enabled");
    check(strcmp(upse_get_custom_bios(), path) == 0, "BIOS path preserved");
    upse_set_custom_bios(NULL);
    check(upse_has_custom_bios() == 0, "BIOS cleared");
}

static void audio_callback(unsigned char *data, long bytes, void *user_data)
{
    (void)data;
    (void)bytes;
    (void)user_data;
}

static void test_configuration_api(void)
{
    upse_set_audio_callback(audio_callback, NULL);
    upse_set_interpolation_mode(1);
    upse_set_interpolation_coefficient(0.75);
    upse_set_reverb_mode(1);
    upse_set_reverb_no_downsample(0);
    upse_set_audio_callback(NULL, NULL);
    check(1, "configuration APIs completed");
}

static void *invalid_open(char *path, char *mode)
{
    (void)path;
    (void)mode;
    return NULL;
}

static size_t invalid_read(void *ptr, size_t size, size_t count, void *stream)
{
    (void)ptr;
    (void)size;
    (void)count;
    (void)stream;
    return 0;
}

static int invalid_seek(void *stream, long offset, int whence)
{
    (void)stream;
    (void)offset;
    (void)whence;
    return -1;
}

static int invalid_close(void *stream)
{
    (void)stream;
    return 0;
}

static void test_invalid_psf(void)
{
    upse_iofuncs_t io = {
        invalid_open,
        invalid_read,
        invalid_seek,
        invalid_close,
    };

    check(upse_get_psf_metadata("invalid.psf", &io) == NULL,
          "invalid PSF metadata rejected");
}

static void test_ohos_abi(void)
{
    check(sizeof(u8) == 1, "u8 width");
    check(sizeof(u16) == 2, "u16 width");
    check(sizeof(u32) == 4, "u32 width");
    check(sizeof(u64) == 8, "u64 width");
    check(sizeof(void *) == 8, "HarmonyOS AArch64 pointer width");
    check(sizeof(uptr) == sizeof(void *), "uptr matches pointer width");
}

int main(void)
{
    test_numeric_api();
    test_bios_api();
    test_configuration_api();
    test_invalid_psf();
    test_ohos_abi();
    printf("UPSE HarmonyOS consumer test: %d assertions passed\n", assertions);
    return EXIT_SUCCESS;
}
