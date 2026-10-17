#include <minidjvu/minidjvu.h>

#include <cstdio>
#include <cstring>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "The HarmonyOS PC package must target aarch64"
#endif

static_assert(sizeof(void *) == 8, "HarmonyOS PC requires a 64-bit ABI");
static_assert(sizeof(int32) == 4, "minidjvu int32 must remain 32-bit on OHOS");

int main()
{
    if (mdjvu_check_sanity() != nullptr) {
        std::fprintf(stderr, "minidjvu ABI sanity failed on HarmonyOS\n");
        return 1;
    }

    mdjvu_bitmap_t bitmap = mdjvu_bitmap_create(65, 1);
    if (!bitmap) {
        std::fprintf(stderr, "failed to create boundary bitmap\n");
        return 2;
    }

    unsigned char input[65] = {};
    unsigned char output[65] = {};
    input[0] = 1;
    input[31] = 1;
    input[32] = 1;
    input[63] = 1;
    input[64] = 1;

    mdjvu_bitmap_pack_row(bitmap, input, 0);
    mdjvu_bitmap_unpack_row_0_or_1(bitmap, output, 0);

    const bool ok = mdjvu_bitmap_get_packed_row_size(bitmap) == 9
        && mdjvu_bitmap_get_mass(bitmap) == 5
        && std::memcmp(input, output, sizeof(input)) == 0;
    mdjvu_bitmap_destroy(bitmap);

    if (!ok) {
        std::fprintf(stderr, "HarmonyOS/aarch64 packed-bitmap boundary check failed\n");
        return 3;
    }

    std::puts("HarmonyOS/aarch64 minidjvu ABI check passed");
    return 0;
}
