/* libb2 (BLAKE2) 0.98.1 —— 比对 **RFC 7693 官方测试向量**（非 dlopen 空壳）。
 *
 * RFC 7693 附录 A：BLAKE2b-512("abc") =
 *   ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d1
 *   7d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923
 * 密码学哈希差一位全变，用官方向量能同时验证算法与字节序，桩实现蒙不过去。
 */
#include <blake2.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main(void) {
    static const unsigned char expect[64] = {
        0xba,0x80,0xa5,0x3f,0x98,0x1c,0x4d,0x0d,0x6a,0x27,0x97,0xb6,0x9f,0x12,0xf6,0xe9,
        0x4c,0x21,0x2f,0x14,0x68,0x5a,0xc4,0xb7,0x4b,0x12,0xbb,0x6f,0xdb,0xff,0xa2,0xd1,
        0x7d,0x87,0xc5,0x39,0x2a,0xab,0x79,0x2d,0xc2,0x52,0xd5,0xde,0x45,0x33,0xcc,0x95,
        0x18,0xd3,0x8a,0xa8,0xdb,0xf1,0x92,0x5a,0xb9,0x23,0x86,0xed,0xd4,0x00,0x99,0x23,
    };
    unsigned char out[64];
    memset(out, 0, sizeof(out));
    /* 签名核对过上游 src/blake2.h：三个指针在前、三个长度在后
     int blake2b(uint8_t *out, const void *in, const void *key,
                 size_t outlen, size_t inlen, size_t keylen); */
    int rc = blake2b(out, "abc", NULL, sizeof(out), 3, 0);
    CHECK(rc == 0, "blake2b() 返回成功");

    printf("     BLAKE2b-512(\"abc\") 前 8 字节: ");
    for (int i = 0; i < 8; ++i) printf("%02x", out[i]);
    printf("\n");
    CHECK(memcmp(out, expect, sizeof(expect)) == 0,
          "BLAKE2b-512(\"abc\") 命中 RFC 7693 官方向量");

    unsigned char other[64];
    blake2b(other, "abd", NULL, sizeof(other), 3, 0);
    CHECK(memcmp(out, other, sizeof(out)) != 0, "改一个字符摘要就变（排除常量实现）");

    if (failures) { fprintf(stderr, "\nlibblake2: %d 项断言失败\n", failures); return 1; }
    printf("\nlibb2 0.98.1: 全部断言通过\n");
    return 0;
}
