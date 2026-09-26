#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "err.h"

/* "123456789" test vector (standard CRC check values) */
static const uint8_t tv[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};

int main(void)
{
    int rc = 0;

    /* checkSum8 / 16 / 32 (additive modulo 2^N)
     * '1'+...+'9' = 0x31..0x39 => sum = 477 = 0x1DD */
    if (checkSum8_Calc((uint8_t *)tv, sizeof(tv)) != 0xDD) {
        printf("FAIL: checkSum8_Calc\n");
        rc = 1;
    } else {
        printf("PASS: checkSum8_Calc = 0xDD\n");
    }
    if (checkSum16_Calc((uint8_t *)tv, sizeof(tv)) != 0x01DD) {
        printf("FAIL: checkSum16_Calc\n");
        rc = 1;
    } else {
        printf("PASS: checkSum16_Calc = 0x01DD\n");
    }
    if (checkSum32_Calc((uint8_t *)tv, sizeof(tv)) != 0x000001DDu) {
        printf("FAIL: checkSum32_Calc\n");
        rc = 1;
    } else {
        printf("PASS: checkSum32_Calc = 0x000001DD\n");
    }

    /* CRC-8/MAXIM (DOW) check value for "123456789" = 0xA1 */
    hcrc8_T crc8 = {.Poly = 0x31, .Init = 0x00, .refIn = true, .refOut = true, .xorOut = 0x00};
    uint8_t c8 = CRC8_Calc(&crc8, (uint8_t *)tv, sizeof(tv));
    if (c8 != 0xA1) {
        printf("FAIL: CRC8_Calc = 0x%02X (expected 0xA1)\n", c8);
        rc = 1;
    } else {
        printf("PASS: CRC8_Calc (MAXIM) = 0xA1\n");
    }

    /* CRC-16/CCITT-FALSE check value for "123456789" = 0x29B1 */
    hcrc16_T crc16 = {.Poly = 0x1021, .Init = 0xFFFF, .refIn = false, .refOut = false, .xorOut = 0x0000};
    uint16_t c16 = CRC16_Calc(&crc16, (uint8_t *)tv, sizeof(tv));
    if (c16 != 0x29B1) {
        printf("FAIL: CRC16_Calc = 0x%04X (expected 0x29B1)\n", c16);
        rc = 1;
    } else {
        printf("PASS: CRC16_Calc (CCITT-FALSE) = 0x29B1\n");
    }

    /* CRC-32 (IEEE) check value for "123456789" = 0xCBF43926 */
    hcrc32_T crc32 = {.Poly = 0x04C11DB7, .Init = 0xFFFFFFFF, .refIn = true, .refOut = true, .xorOut = 0xFFFFFFFF};
    uint32_t c32 = CRC32_Calc(&crc32, (uint8_t *)tv, sizeof(tv));
    if (c32 != 0xCBF43926u) {
        printf("FAIL: CRC32_Calc = 0x%08X (expected 0xCBF43926)\n", c32);
        rc = 1;
    } else {
        printf("PASS: CRC32_Calc (IEEE) = 0xCBF43926\n");
    }

    if (rc == 0) {
        printf("test error-detection 2.1.1: ALL TESTS PASSED\n");
    }
    return rc;
}
