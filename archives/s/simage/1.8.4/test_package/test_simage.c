/* Consumer test for simage 1.8.4 on HarmonyOS PC
 * Real API coverage: simage_version, simage_check_supported,
 * simage_next_power_of_two, simage_resize + free, check_save_supported.
 * Emits HMBS_TEST_PACKAGE_RESULT after real assertions.
 * Note: simage_check_supported() probes file header via fopen+identify,
 * so we create minimal temp files with correct magic bytes for the test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <simage.h>

static void create_rgb_file(const char *path) {
    FILE *fp = fopen(path, "wb");
    if (fp) {
        unsigned char hdr[2] = {0x01, 0xDA};
        fwrite(hdr, 1, 2, fp);
        /* pad to make file non-empty; loader only checks first 2 bytes */
        unsigned char pad[16] = {0};
        fwrite(pad, 1, sizeof(pad), fp);
        fclose(fp);
    }
}
static void create_unsupported_file(const char *path) {
    FILE *fp = fopen(path, "wb");
    if (fp) {
        const char *data = "XYZ_UNRECOGNIZED_HEADER_FOR_SIMAGE_TEST";
        fwrite(data, 1, strlen(data), fp);
        fclose(fp);
    }
}

int main(void) {
    const int discovered = 3;
    int passed = 0;

    /* Case 1: version must be 1.8.4 */
    {
        int major=0, minor=0, micro=0;
        simage_version(&major, &minor, &micro);
        printf("simage_version: %d.%d.%d\n", major, minor, micro);
        if (major==1 && minor==8 && micro==4) {
            ++passed;
        } else {
            printf("FAIL: version mismatch expected 1.8.4 got %d.%d.%d\n", major, minor, micro);
        }
    }

    /* Case 2: check_supported for builtin vs unknown, plus power-of-two
     * Need real files because simage_check_supported opens and identifies via header.
     * Create temp files in current directory (writable build dir).
     */
    {
        const char *rgb_path = "tmp_test_simage_rgb.rgb";
        const char *unsup_path = "tmp_test_simage_unsup.xyz";
        create_rgb_file(rgb_path);
        create_unsupported_file(unsup_path);

        int rgb_supported = simage_check_supported(rgb_path);
        int xyz_supported = simage_check_supported(unsup_path);
        int pow2_300 = simage_next_power_of_two(300);
        int pow2_512 = simage_next_power_of_two(512);
        int pow2_1 = simage_next_power_of_two(1);
        int save_rgb = simage_check_save_supported("rgb");
        printf("check_supported rgb=%d xyz=%d save_rgb=%d pow2(300)=%d pow2(512)=%d pow2(1)=%d\n",
               rgb_supported, xyz_supported, save_rgb, pow2_300, pow2_512, pow2_1);
        /* builtin rgb should be supported (header 0x01DA), unknown should not, pow2 checks */
        if (rgb_supported==1 && xyz_supported==0 && pow2_300==512 && pow2_512==512 && pow2_1==1) {
            ++passed;
        } else {
            printf("FAIL: check_supported/pow2 unexpected (rgb %d xyz %d pow2 %d %d %d)\n",
                   rgb_supported, xyz_supported, pow2_300, pow2_512, pow2_1);
        }
        remove(rgb_path);
        remove(unsup_path);
    }

    /* Case 3: resize 2x2 -> 1x1 and free */
    {
        unsigned char img[12] = {
            255,0,0,   0,255,0,
            0,0,255,   255,255,0
        };
        unsigned char *resized = simage_resize(img, 2, 2, 3, 1, 1);
        if (resized) {
            printf("resize 2x2->1x1 ok, first pixel %d %d %d\n", resized[0], resized[1], resized[2]);
            simage_free_image(resized);
            ++passed;
        } else {
            const char *err = simage_get_last_error();
            printf("FAIL: simage_resize returned NULL err=%s\n", err ? err : "(null)");
        }
    }

    printf("simage consumer: %d/%d cases passed\n", passed, discovered);
    int ok = (passed == discovered);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"test_simage\",\"discovered\":%d,\"passedCount\":%d}\n",
           ok ? "true" : "false", discovered, passed);
    return ok ? 0 : 1;
}
