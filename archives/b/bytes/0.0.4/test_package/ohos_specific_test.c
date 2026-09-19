/*
 * ohos_specific_test.c — bytes 0.0.4 HarmonyOS 专项测试
 *
 * 本测试为鸿蒙适配专项新增用例（区别于上游 test.c 与 test_package 消费者测试）：
 * 1. 验证 string_to_bytes 对 >4GB long long 值的换算与无后缀纯数字解析；
 * 2. 验证 bytes_to_string 返回的字符串内存可由 free() 正常释放（asprintf 路径，
 *    在 OHOS 目标运行时上的真实可观察行为）；
 * 3. 验证 gb 分支整除截断语义。
 *
 * 为什么用自带 CHECK 宏而不是 assert()：R02 评审指出本仓库 profile 为
 * build_type=Release，CMake 内建 CMAKE_C_FLAGS_RELEASE 自带 -DNDEBUG，assert()
 * 被编译期移除导致"断言数 > 0 但实际不判"的假绿；自带 CHECK 宏不受 NDEBUG
 * 影响，始终真实求值，并把 checks=<N> failures=0 打成机器可读证据行。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bytes.h"

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond, what)                                                       \
    do {                                                                        \
        g_checks++;                                                             \
        if (!(cond)) {                                                          \
            g_failures++;                                                       \
            printf("FAIL: %s\n", (what));                                       \
        }                                                                       \
    } while (0)

#define CHECK_IS(value, expected, what)                                         \
    CHECK((value) == (expected), (what))

static void
test_ohos_boundary_values(void) {
  /* >4GB 的 long long 换算（arm64 上 64 位 long long 语义） */
  CHECK_IS(string_to_bytes("2gb"), 2LL * 1024 * 1024 * 1024, "2gb -> 2*1024^3");
  CHECK_IS(string_to_bytes("10gb"), 10LL * 1024 * 1024 * 1024, "10gb -> 10*1024^3");
  /* 无后缀纯数字：strtoll("0")==0，上游 bytes.c `if (!val) return -1;` 返回 -1 */
  CHECK_IS(string_to_bytes("0"), -1, "\"0\" -> -1 (upstream !val return -1)");
  /* kb 与 mb 换算 */
  CHECK_IS(string_to_bytes("1gb"), 1024LL * 1024 * 1024, "1gb -> 1024^3");
  CHECK_IS(string_to_bytes("512kb"), 512 * 1024, "512kb -> 512*1024");
}

static void
test_ohos_asprintf_memory(void) {
  /* bytes_to_string 内部使用 asprintf 分配内存，验证可观察结果与可释放性 */
  char *s = bytes_to_string(2LL * 1024 * 1024 * 1024);
  CHECK(s != NULL, "bytes_to_string(2gb) != NULL");
  CHECK_IS(strcmp(s, "2gb"), 0, "bytes_to_string(2gb) == \"2gb\"");
  printf("bytes_to_string(2gb) = \"%s\"\n", s);
  free(s);  /* 若 OHOS libc 的 asprintf 分配不可释放，此处会触发运行时错误 */

  s = bytes_to_string(0);
  CHECK(s != NULL, "bytes_to_string(0) != NULL");
  printf("bytes_to_string(0) = \"%s\"\n", s);
  free(s);
}

static void
test_ohos_gb_div_truncation(void) {
  /* gb 分支按 1024^3 整除（bytes.c: bytes / GB），验证整除语义 */
  long long raw = (1024LL * 1024 * 1024) + 512LL * 1024 * 1024; /* 1.5gb */
  char *s = bytes_to_string(raw);
  CHECK_IS(strcmp(s, "1gb"), 0, "bytes_to_string(1.5gb) truncates to \"1gb\"");
  printf("bytes_to_string(1.5gb) = \"%s\" (truncated)\n", s);
  free(s);
}

int
main(void) {
  test_ohos_boundary_values();
  test_ohos_asprintf_memory();
  test_ohos_gb_div_truncation();
  printf("\n  checks=%d failures=%d\n", g_checks, g_failures);
  if (g_failures > 0) {
    printf("\n  \x1b[31m\xe2\x9c\x97 \x1b[90mohos-specific tests FAILED\x1b[0m\n\n");
    return 1;
  }
  printf("\n  \x1b[32m\xe2\x9c\x93 \x1b[90mohos-specific tests ok\x1b[0m\n\n");
  return 0;
}