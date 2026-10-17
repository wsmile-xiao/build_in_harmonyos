/* test.c — asmix 1.5 test_package 真实测试程序（R34 非空壳）
 *
 * 读取安装产物 asmix 二进制，校验其为 arm64 ELF 可执行文件：
 *  1. ELF magic（0x7f 'E' 'L' 'F'）
 *  2. e_machine == EM_AARCH64 (183)
 * 二进制路径由 CMake 编译期宏 ASMIX_BIN_PATH 注入（test_package 已知包路径）。
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#ifndef ASMIX_BIN_PATH
#define ASMIX_BIN_PATH "/nonexistent"
#endif

int main(void) {
    FILE *fp = fopen(ASMIX_BIN_PATH, "rb");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot open asmix binary: %s\n", ASMIX_BIN_PATH);
        return 1;
    }

    unsigned char hdr[20];
    if (fread(hdr, 1, sizeof(hdr), fp) != sizeof(hdr)) {
        fprintf(stderr, "FAIL: cannot read ELF header\n");
        fclose(fp);
        return 1;
    }
    fclose(fp);

    /* ELF magic: 0x7f 'E' 'L' 'F' */
    if (hdr[0] != 0x7f || memcmp(hdr + 1, "ELF", 3) != 0) {
        fprintf(stderr, "FAIL: not an ELF file\n");
        return 1;
    }
    /* e_machine (offset 18, little-endian) == EM_AARCH64 = 183 */
    uint16_t e_machine = (uint16_t)(hdr[18] | (hdr[19] << 8));
    if (e_machine != 183) {
        fprintf(stderr, "FAIL: not AArch64 ELF, e_machine=%u\n", (unsigned)e_machine);
        return 1;
    }

    printf("PASS: asmix 产物为 arm64 ELF 可执行文件（ELF magic + e_machine 校验）\n");
    return 0;
}
