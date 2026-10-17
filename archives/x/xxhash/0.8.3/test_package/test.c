/* xxHash 0.8.3 —— 比对**官方已知测试向量**（非 dlopen 空壳）。
 *
 * 上游 README/测试里给出的向量：
 *   XXH64("", 0)      == 0xEF46DB3751D8E999
 *   XXH32("", 0)      == 0x02CC5D05
 * 哈希函数是「差一位就全变」的，用已知向量能同时验证
 * 算法正确性与字节序处理 —— 桩实现绝无可能蒙对。
 */
#include <xxhash.h>

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main(void) {
    unsigned v = XXH_versionNumber();
    printf("     xxHash 版本号: %u\n", v);
    CHECK(v >= 800, "XXH_versionNumber() >= 800（0.8.x）");

    XXH64_hash_t h64 = XXH64("", 0, 0);
    printf("     XXH64(\"\") = 0x%016" PRIx64 "\n", (uint64_t)h64);
    CHECK(h64 == 0xEF46DB3751D8E999ULL, "XXH64(空串) 命中官方向量 0xEF46DB3751D8E999");

    XXH32_hash_t h32 = XXH32("", 0, 0);
    printf("     XXH32(\"\") = 0x%08x\n", (unsigned)h32);
    CHECK(h32 == 0x02CC5D05U, "XXH32(空串) 命中官方向量 0x02CC5D05");

    /* 再验「输入变则输出变」，排除「永远返回同一常量」的实现 */
    XXH64_hash_t a = XXH64("harmony", 7, 0);
    XXH64_hash_t b = XXH64("harmonY", 7, 0);
    CHECK(a != b, "改一个字符哈希就变（排除常量实现）");

    if (failures) { fprintf(stderr, "\nxxhash: %d 项断言失败\n", failures); return 1; }
    printf("\nxxHash 0.8.3: 全部断言通过\n");
    return 0;
}
