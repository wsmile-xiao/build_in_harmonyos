/* test.c — bytes 0.0.4 消费者测试（test_package）
 *
 * 仅通过公开头文件 bytes.h 调用公开 API（string_to_bytes / bytes_to_string），
 * 验证第三方使用者能编译、链接、调用并得到可观察结果。
 *
 * 为什么用自带 CHECK 宏而不是 assert()：R02 评审指出本仓库 profile 为
 * build_type=Release，CMake 内建 CMAKE_C_FLAGS_RELEASE 自带 -DNDEBUG，assert()
 * 被编译期移除导致假绿；自带 CHECK 宏不受 NDEBUG 影响，始终真实求值，
 * 并把 checks=<N> failures=0 打成机器可读证据行。
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

int
main(void) {
  long long n;

  n = string_to_bytes("100");
  printf("string_to_bytes(\"100\") = %lld\n", n);
  CHECK_IS(n, 100, "string_to_bytes(\"100\") == 100");

  n = string_to_bytes("1kb");
  printf("string_to_bytes(\"1kb\") = %lld\n", n);
  CHECK_IS(n, 1024, "string_to_bytes(\"1kb\") == 1024");

  n = string_to_bytes("5mb");
  printf("string_to_bytes(\"5mb\") = %lld\n", n);
  CHECK_IS(n, 5LL * 1024 * 1024, "string_to_bytes(\"5mb\") == 5*1024^2");

  n = string_to_bytes("1gb");
  printf("string_to_bytes(\"1gb\") = %lld\n", n);
  CHECK_IS(n, 1024LL * 1024 * 1024, "string_to_bytes(\"1gb\") == 1024^3");

  {
    char *s = bytes_to_string(100);
    printf("bytes_to_string(100) = \"%s\"\n", s);
    CHECK_IS(strcmp(s, "100b"), 0, "bytes_to_string(100) == \"100b\"");
    free(s);
  }

  {
    char *s = bytes_to_string(1024);
    printf("bytes_to_string(1024) = \"%s\"\n", s);
    CHECK_IS(strcmp(s, "1kb"), 0, "bytes_to_string(1024) == \"1kb\"");
    free(s);
  }

  {
    char *s = bytes_to_string(5LL * 1024 * 1024 * 1024);
    printf("bytes_to_string(5gb) = \"%s\"\n", s);
    CHECK_IS(strcmp(s, "5gb"), 0, "bytes_to_string(5gb) == \"5gb\"");
    free(s);
  }

  printf("\n  checks=%d failures=%d\n", g_checks, g_failures);
  if (g_failures > 0) {
    printf("\n  \x1b[31m\xe2\x9c\x97 \x1b[90mtest_package consumer FAILED\x1b[0m\n\n");
    return 1;
  }
  printf("\n  \x1b[32m\xe2\x9c\x93 \x1b[90mtest_package consumer ok\x1b[0m\n\n");
  return 0;
}