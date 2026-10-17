#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <checksum.h>

/* 消费者验证：仅通过 libcrc 公开头文件 checksum.h 与静态库 libcrc.a 链接，
 * 调用公开 API 并对上游已知向量断言，验证编译、链接、运行三个环节。 */

static int failures = 0;

static void expect_u8(const char *name, uint8_t got, uint8_t want) {
    if (got != want) {
        printf("FAIL %s: got 0x%02X want 0x%02X\n", name, got, want);
        failures++;
    }
}

static void expect_u16(const char *name, uint16_t got, uint16_t want) {
    if (got != want) {
        printf("FAIL %s: got 0x%04X want 0x%04X\n", name, got, want);
        failures++;
    }
}

static void expect_u32(const char *name, uint32_t got, uint32_t want) {
    if (got != want) {
        printf("FAIL %s: got 0x%08X want 0x%08X\n", name, got, want);
        failures++;
    }
}

int main(void) {
    const unsigned char data[] = "123456789";
    size_t len = strlen((const char *) data);

    /* 上游 test/testcrc.c 的已知向量表（checks[] 第一项） */
    expect_u8("crc_8", crc_8(data, len), 0xA2);
    expect_u16("crc_16", crc_16(data, len), 0xBB3D);
    expect_u32("crc_32", crc_32(data, len), 0xCBF43926);
    expect_u16("crc_dnp", crc_dnp(data, len), 0x82EA);
    expect_u16("crc_modbus", crc_modbus(data, len), 0x4B37);
    expect_u16("crc_sick", crc_sick(data, len), 0x56A6);
    expect_u16("crc_xmodem", crc_xmodem(data, len), 0x31C3);
    expect_u16("crc_ccitt_1d0f", crc_ccitt_1d0f(data, len), 0xE5CC);
    expect_u16("crc_ccitt_ffff", crc_ccitt_ffff(data, len), 0x29B1);
    expect_u16("crc_kermit", crc_kermit(data, len), 0x8921);

    /* NMEA checksum：checksum_NMEA 返回不带 '*' 前缀的两位十六进制校验串 */
    unsigned char buf[4];
    const char *nmea = checksum_NMEA((const unsigned char *) "$GPGGA,092750.000,5321.6802,N,00630.3372,W,1,8,1.03,61.7,M,55.2,M,,*76", buf);
    (void) nmea;
    if (strcmp((char *) buf, "76") != 0) {
        printf("FAIL checksum_NMEA: got \"%s\" want \"76\"\n", buf);
        failures++;
    }

    if (failures == 0) {
        printf("test_libcrc: ALL 11 consumer checks PASSED\n");
        return 0;
    }
    printf("test_libcrc: %d checks FAILED\n", failures);
    return 1;
}
