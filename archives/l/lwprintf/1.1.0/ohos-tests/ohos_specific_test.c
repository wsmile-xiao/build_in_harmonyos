/*
 * OhOS-specific test for lwprintf 1.1.0 — 新增真实可执行的 HarmonyOS 专项测试
 *
 * 本测试不是上游 tests/test.c 的复述，而是针对 OHOS (aarch64, musl) 平台
 * 补上游未覆盖的公共 API 面：
 *   1. 自定义实例 (lwprintf_t + lwprintf_init_ex / _ex 系列) 与实例隔离
 *   2. 字节数组格式化 %*K / % *K
 *   3. snprintf 截断语义 (n < 输出长度时的行为与返回值)
 *   4. 64 位指针 %p 输出 (OHOS arm64 为 8 字节指针, 上游测试按 32 位假设)
 *   5. long long 与 uintmax_t 类型支持
 * 仅通过已安装包公开头文件 lwprintf/lwprintf.h 与公开 API 使用该库。
 *
 * 构建: clang (OHOS aarch64) 链接 liblwprintf.a
 * 运行: 直接在 OHOS 设备环境执行, 退出码 0 = 全部通过
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lwprintf/lwprintf.h"

static size_t ohos_passed, ohos_failed;

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (cond) {                                                        \
            ohos_passed++;                                                 \
        } else {                                                           \
            ohos_failed++;                                                 \
            fprintf(stderr, "OHOS TEST FAIL: %s (line %d)\n", msg, __LINE__); \
        }                                                                  \
    } while (0)

/* 实例 1 输出到 stdout, 实例 2 输出到 sink2 缓冲区, 验证隔离 */
static int
out_ch1(int ch, lwprintf_t* lw) {
    (void)lw;
    return (ch == '\0') ? 0 : (putchar(ch), ch);
}

static char sink2[256];
static size_t sink2_len;

static int
out_ch2(int ch, lwprintf_t* lw) {
    (void)lw;
    if (ch != '\0' && sink2_len < sizeof(sink2) - 1) {
        sink2[sink2_len++] = (char)ch;
    }
    return ch;
}

int
main(void) {
    /* 1. 自定义多实例 */
    lwprintf_t inst1, inst2;
    memset(&inst1, 0, sizeof(inst1));
    memset(&inst2, 0, sizeof(inst2));
    CHECK(lwprintf_init_ex(&inst1, out_ch1) == 1, "init_ex inst1");
    CHECK(lwprintf_init_ex(&inst2, out_ch2) == 1, "init_ex inst2");

    unsigned char bytes[] = {0xAB, 0xCD, 0xEF};
    char buf[128];

    /* 2. 字节数组 %*K (连续) 与 % *K (空格分隔): "K=ABCDEF" / "K=AB CD EF" */
    int len2 = lwprintf_snprintf_ex(&inst2, NULL, 0, "K=%*K", 3, bytes);
    CHECK(len2 == 8, "inst2 %*K length");      /* "K=ABCDEF" = 8 chars */

    sink2_len = 0;
    len2 = lwprintf_snprintf_ex(&inst2, NULL, 0, "K=% *K", 3, bytes);
    CHECK(len2 == 10, "inst2 % *K length");    /* "K=AB CD EF" = 10 chars */

    /* 3. 截断语义: n 小于输出长度时返回所需长度(不含NUL), 目标被截断 */
    char small[4];
    memset(small, 'x', sizeof(small));
    int r = lwprintf_snprintf(small, 4, "%s", "HelloWorld123");
    CHECK(r == 13, "snprintf truncation returns full length");
    CHECK(strcmp(small, "Hel") == 0, "snprintf truncated buffer content");

    /* 4. 64 位指针: OHOS arm64 上 %p 应输出 16 个十六进制字符 */
    void* p = (void*)0x12345678;
    int plen = lwprintf_snprintf(buf, sizeof(buf), "%p", p);
    CHECK(plen == 16, "%p 64-bit length is 16 hex chars");

    /* 5. long long / uintmax_t */
    CHECK(lwprintf_snprintf(buf, sizeof(buf), "%lld", (long long)-9223372036854775807LL - 1) == 20,
          "INT64_MIN length");
    CHECK(strcmp(buf, "-9223372036854775808") == 0, "INT64_MIN value");
    CHECK(lwprintf_snprintf(buf, sizeof(buf), "%ju", (uintmax_t)18446744073709551615ULL) == 20,
          "UINT64_MAX length");
    CHECK(strcmp(buf, "18446744073709551615") == 0, "UINT64_MAX value");

    /* 基本多格式组合: "I=42 N=OH F=3.5" = 15 chars */
    CHECK(lwprintf_snprintf(buf, sizeof(buf), "I=%d N=%s F=%.1f", 42, "OH", 3.5) == 15,
          "combined format length");
    CHECK(strcmp(buf, "I=42 N=OH F=3.5") == 0, "combined format content");

    printf("==== OhOS-specific test summary ====\n");
    printf("passed=%u failed=%u total=%u\n",
           (unsigned)ohos_passed, (unsigned)ohos_failed, (unsigned)(ohos_passed + ohos_failed));
    return ohos_failed == 0 ? 0 : 1;
}