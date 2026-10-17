/* test.c — wmsmixer 0.5.1 test_package 消费者测试（R34 真实消费者用例）
 *
 * 两项真实校验：
 *  1. 产物校验：读取安装产物 wmsmixer 二进制，校验为 arm64 ELF 可执行文件
 *     （ELF magic + e_machine == EM_AARCH64 (183)）。
 *  2. 端到端消费者用例：执行 `wmsmixer --version`，验证进程退出码为 0 且
 *     输出包含版本号 "0.5.1"（该参数路径在 X 连接前处理并 exit(0)，无显示
 *     环境可运行，验证二进制可加载、命令行解析与版本报告功能真实可用）。
 * 二进制路径由编译期宏 WMSMIXER_BIN_PATH 注入（test_package 已知包路径）。
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#ifndef WMSMIXER_BIN_PATH
#define WMSMIXER_BIN_PATH "/nonexistent"
#endif

static int check_elf(const char *path) {
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot open wmsmixer binary: %s\n", path);
        return 1;
    }
    unsigned char hdr[20];
    if (fread(hdr, 1, sizeof(hdr), fp) != sizeof(hdr)) {
        fprintf(stderr, "FAIL: cannot read ELF header\n");
        fclose(fp);
        return 1;
    }
    fclose(fp);
    if (hdr[0] != 0x7f || memcmp(hdr + 1, "ELF", 3) != 0) {
        fprintf(stderr, "FAIL: not an ELF file\n");
        return 1;
    }
    uint16_t e_machine = (uint16_t)(hdr[18] | (hdr[19] << 8));
    if (e_machine != 183) {
        fprintf(stderr, "FAIL: not AArch64 ELF, e_machine=%u\n", (unsigned)e_machine);
        return 1;
    }
    printf("PASS[1/2]: wmsmixer 产物为 arm64 ELF 可执行文件（ELF magic + e_machine 校验）\n");
    return 0;
}

static int check_version(const char *path) {
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", path);
    FILE *p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FAIL: cannot execute wmsmixer --version\n");
        return 1;
    }
    char out[4096];
    size_t n = fread(out, 1, sizeof(out) - 1, p);
    out[n] = '\0';
    int rc = pclose(p);
    if (rc != 0) {
        fprintf(stderr, "FAIL: wmsmixer --version exit=%d, output:\n%s\n", rc, out);
        return 1;
    }
    if (strstr(out, "wmsmixer version") == NULL || strstr(out, "0.5.1") == NULL) {
        fprintf(stderr, "FAIL: --version 输出缺少版本信息, output:\n%s\n", out);
        return 1;
    }
    printf("PASS[2/2]: wmsmixer --version 端到端运行成功，输出包含版本 0.5.1\n");
    return 0;
}

int main(void) {
    if (check_elf(WMSMIXER_BIN_PATH) != 0)
        return 1;
    if (check_version(WMSMIXER_BIN_PATH) != 0)
        return 1;
    printf("ALL PASS: wmsmixer 0.5.1 产物校验与端到端消费者用例通过\n");
    return 0;
}
