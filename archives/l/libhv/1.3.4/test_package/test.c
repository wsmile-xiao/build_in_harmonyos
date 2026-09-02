/*
 * test_libhv.c — Conan test_package 消费者测试（真实调用 libhv C API）
 *
 * 验证安装后的 libhv 包可被下游消费者链接并使用：
 *   - base64: 已知答案往返
 *   - md5:    已知答案
 *   - hbase:  hv_rand 范围 + hv_random_string 生成
 * 任一断言失败 -> 非 0 退出。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "hv/hbase.h"
#include "hv/base64.h"
#include "hv/md5.h"

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); ++failures; } \
} while (0)

int main(void) {
    printf("=== libhv 1.3.4 consumer test (test_package) ===\n");

    // base64 encode("hello") -> "aGVsbG8="
    char enc[64] = {0};
    int n = hv_base64_encode((const unsigned char*)"hello", 5, enc);
    CHECK(n > 0 && strcmp(enc, "aGVsbG8=") == 0, "hv_base64_encode(\"hello\")==aGVsbG8=");
    // base64 decode roundtrip
    unsigned char dec[64] = {0};
    int dn = hv_base64_decode("aGVsbG8=", 8, dec);
    CHECK(dn > 0 && strncmp((char*)dec, "hello", 5) == 0, "hv_base64_decode 往返一致");

    // md5 known answer: "hello" -> 5d41402abc4b2a76b9719d911017c592
    char hex[64] = {0};
    hv_md5_hex((unsigned char*)"hello", 5, hex, sizeof(hex));
    CHECK(strcmp(hex, "5d41402abc4b2a76b9719d911017c592") == 0,
          "hv_md5_hex(\"hello\") 已知答案匹配");

    // hbase: rand range + random string
    int r = hv_rand(10, 99);
    CHECK(r >= 10 && r <= 99, "hv_rand 落在 [10,99]");
    char buf[16] = {0};
    char* rb = hv_random_string(buf, 8);
    CHECK(rb == buf && strlen(buf) == 8, "hv_random_string 生成 8 字符");

    printf("=== consumer test result: %d failure(s) ===\n", failures);
    return failures == 0 ? 0 : 1;
}
