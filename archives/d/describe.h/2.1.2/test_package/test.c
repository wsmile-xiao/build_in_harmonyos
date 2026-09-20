// test_package/test.c — describe.h 2.1.2 消费者验证
// 真实调用被测包 API（R34）：
//   - describe/it BDD 宏套件
//   - assert_* 宏族（assert_equal / assert_str_equal / assert_null 等）
//   - assert_failures() 失败计数机制
#include <stdio.h>
#include "describe.h"

int main(void) {
  describe("describe.h on HarmonyOS") {
    it("should run a passing case") {
      assert(1 == 1);
    }

    it("should evaluate expressions") {
      int a = 6;
      int b = 7;
      assert(a * b == 42);
    }

    it("should bundle assertion macros") {
      assert_equal(1, 1);
      assert_not_equal(1, 2);
      assert_str_equal("hello", "hello");
      assert_str_not_equal("hello", "world");
      assert_strn_equal("abc", "abd", 2);
      assert_null(NULL);
      assert_not_null("not null");
    }
  }

  // 失败计数机制：上述用例全部通过，assert_failures() 应为 0
  int rc = assert_failures();
  if (rc != 0) {
    fprintf(stderr, "FAIL: expected 0 failures, got %d\n", rc);
    return 1;
  }

  printf("describe.h consumer test: PASS\n");
  return 0;
}
