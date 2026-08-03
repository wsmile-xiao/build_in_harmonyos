// test_package/test_blisp.c — consumer smoke test for libblisp.
// Exercises the public C API declared in <blisp_util.h> and <blisp_chip.h>:
//   crc32_calculate() — pure computation, no hardware required.
//   blisp_chip_bl60x  — global chip descriptor, verifies symbol linking.
#include <stdint.h>
#include <blisp_util.h>
#include <blisp_chip.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int ok = 1;
    int passed = 0;

    // CRC32 of "123456789" with the standard CRC32 polynomial (0x04C11DB7,
    // reflected, XorIn/XorOut = 0xFFFFFFFF) is 0xCBF43926. This is the
    // canonical check value from the CRC32 test suite.
    const char *data = "123456789";
    uint32_t crc = crc32_calculate(data, strlen(data));
    if (crc != 0xCBF43926u) {
        printf("FAIL: crc32_calculate(\"123456789\") = 0x%08X, expected 0xCBF43926\n", crc);
        ok = 0;
    } else {
        passed++;
        printf("PASS: crc32_calculate(\"123456789\") = 0x%08X\n", crc);
    }

    // Verify the BL60X chip descriptor is linked and has correct type.
    if (blisp_chip_bl60x.type != BLISP_CHIP_BL60X) {
        printf("FAIL: blisp_chip_bl60x.type = %d, expected %d (BLISP_CHIP_BL60X)\n",
               blisp_chip_bl60x.type, BLISP_CHIP_BL60X);
        ok = 0;
    } else {
        passed++;
        printf("PASS: blisp_chip_bl60x.type = BLISP_CHIP_BL60X, type_str = \"%s\"\n",
               blisp_chip_bl60x.type_str ? blisp_chip_bl60x.type_str : "(null)");
    }

    // Verify the BL70X chip descriptor as well.
    if (blisp_chip_bl70x.type != BLISP_CHIP_BL70X) {
        printf("FAIL: blisp_chip_bl70x.type = %d, expected %d (BLISP_CHIP_BL70X)\n",
               blisp_chip_bl70x.type, BLISP_CHIP_BL70X);
        ok = 0;
    } else {
        passed++;
        printf("PASS: blisp_chip_bl70x.type = BLISP_CHIP_BL70X, type_str = \"%s\"\n",
               blisp_chip_bl70x.type_str ? blisp_chip_bl70x.type_str : "(null)");
    }

    // Empty-buffer CRC32 should equal 0x00000000 (0xFFFFFFFF XOR 0xFFFFFFFF).
    uint32_t crc_empty = crc32_calculate("", 0);
    if (crc_empty != 0x00000000u) {
        printf("FAIL: crc32_calculate(\"\",0) = 0x%08X, expected 0x00000000\n", crc_empty);
        ok = 0;
    } else {
        passed++;
        printf("PASS: crc32_calculate(\"\",0) = 0x%08X\n", crc_empty);
    }

    if (ok) {
        printf("blisp 0.0.5: all %d assertions passed\n", passed);
        return 0;
    }
    printf("blisp 0.0.5: test FAILED\n");
    return 1;
}
