// HarmonyOS 专项测试：shoco master 真实消费入口验证
// 使用 OHOS armv8 工具链（clang 15 / aarch64-linux-ohos）实际编译并运行，
// 覆盖 OHOS PC 平台真实场景：UTF-8 中文短文本、ASCII 混合串、空串、
// 截断压缩输入的解压边界，验证 shoco 公开 API 在 OHOS 下的正确性。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "shoco.h"

static int failures = 0;

static void roundtrip(const char *label, const char *in, size_t len) {
    char comp[4096];
    char out[4096];
    size_t comp_len, out_len;

    comp_len = shoco_compress(in, len, comp, sizeof(comp));
    if (comp_len > sizeof(comp)) {
        printf("FAIL[%s]: compress bufsize overflow ret=%zu\n", label, comp_len);
        failures++;
        return;
    }
    out_len = shoco_decompress(comp, comp_len, out, sizeof(out));
    if (out_len > sizeof(out)) {
        printf("FAIL[%s]: decompress bufsize overflow ret=%zu\n", label, out_len);
        failures++;
        return;
    }
    if (out_len != len || memcmp(out, in, len) != 0) {
        printf("FAIL[%s]: roundtrip mismatch in=%zu out=%zu\n", label, len, out_len);
        failures++;
    }
}

int main(void) {
    /* 1) UTF-8 中文短文本（OHOS PC 应用 UI/日志常见负载） */
    const char *zh = "鸿蒙操作系统 HarmonyOS 应用适配测试 你好世界";
    roundtrip("utf8-zh", zh, strlen(zh));

    /* 2) 含 ASCII 数字/符号的混合短串 */
    const char *mix = "apt-get install libshoco 2026-09-17 /data/app 80%";
    roundtrip("mixed", mix, strlen(mix));

    /* 3) 空字符串（len=0，API 约定按 null-terminated 处理） */
    roundtrip("empty", "", 0);

    /* 4) 单字符与超短串 */
    roundtrip("single", "a", 1);
    roundtrip("short", "hi", 2);

    /* 5) 截断压缩输入的解压边界：不完整编码不得崩溃 */
    {
        char comp[64];
        size_t clen = shoco_compress("hello world", 0, comp, sizeof(comp));
        char out[64];
        size_t r = shoco_decompress(comp, clen - 1, out, sizeof(out));
        if (r == (size_t)-1) {
            printf("INFO[truncated]: decompress rejected truncated input (ret=SIZE_MAX)\n");
        } else {
            printf("INFO[truncated]: decompress tolerated truncated input (ret=%zu)\n", r);
        }
    }

    /* 6) CLI 产物存在性：shoco 二进制应可由公开构建产出（R38 声明） */
    if (system("command -v shoco >/dev/null 2>&1") != 0) {
        printf("WARN: 'shoco' CLI not in PATH (expected during in-tree test run)\n");
    }

    if (failures == 0) {
        puts("OHOS special test: all checks passed.");
        return 0;
    }
    printf("OHOS special test: %d failure(s).\n", failures);
    return 1;
}
