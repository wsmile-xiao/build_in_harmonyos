/* test_zpl.c — Conan test_package 消费者测试（真实调用 zpl 公开 API）。
 *
 * zpl 为单头文件库：在唯一源文件中先 #define ZPL_IMPLEMENTATION 再
 * #include <zpl.h>。本测试实际调用 base64 编解码往返、字符串构建与
 * hash 计算三类公开 API，断言可观察结果并打印（R34：禁止空壳）。 */
#define ZPL_IMPLEMENTATION
#include <zpl.h>

int main(void)
{
    int failures = 0;

    /* 1. base64 编解码往返 */
    {
        char const *plain = "Hello HarmonyOS zpl consumer!";
        zpl_u8 *enc = zpl_base64_encode(zpl_heap(), plain, zpl_strlen(plain));
        if (!enc) { zpl_printf("FAIL: base64 encode returned NULL\n"); return 1; }
        zpl_u8 *dec = zpl_base64_decode(zpl_heap(), enc, zpl_strlen(enc));
        if (!dec) { zpl_printf("FAIL: base64 decode returned NULL\n"); return 1; }
        if (zpl_strcmp(plain, dec) != 0) {
            zpl_printf("FAIL: base64 round-trip mismatch\n");
            failures++;
        } else {
            zpl_printf("base64 round-trip OK: '%s'\n", dec);
        }
    }

    /* 2. 字符串构建（zpl_string_sprintf_buf 为 varargs 便捷封装，
     *    内部使用本地持久缓冲区（zpl_local_persist）再 zpl_string_make） */
    {
        zpl_string s = zpl_string_sprintf_buf(zpl_heap(), "zpl-%d-%s", 9, "8.0");
        if (!s) { zpl_printf("FAIL: zpl_string_sprintf returned NULL\n"); return 1; }
        if (zpl_strcmp(s, "zpl-9-8.0") != 0) {
            zpl_printf("FAIL: string build mismatch: '%s'\n", s);
            failures++;
        } else {
            zpl_printf("string build OK: '%s'\n", s);
        }
        zpl_string_free(s);
    }

    /* 3. hash 计算（可观察结果） */
    {
        zpl_u64 h = zpl_fnv64a("consumer-check", zpl_strlen("consumer-check"));
        zpl_printf("fnv64a hash OK: 0x%016llx\n", (unsigned long long)h);
        if (h == 0) failures++;
    }

    if (failures) {
        zpl_printf("test_zpl: %d failure(s)\n", failures);
        return 1;
    }
    zpl_printf("test_zpl: ALL OK\n");
    return 0;
}
