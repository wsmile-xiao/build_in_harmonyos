/* test_package 消费者验证：通过 iowow 已安装公开头文件调用真实公开 API。
 * R34：必须调用被测包 API 并验证可观察结果，禁止空壳打印。
 * 验证点：
 *   1. iw_init() 初始化返回 0
 *   2. iwxstr（字符串构建器）创建/追加/取内容/释放全链路
 *   3. 内容正确性断言（append 后长度与内容一致）
 */
#include <stdio.h>
#include <string.h>
#include <iowow/iwxstr.h>
#include <iowow/iwlog.h>

static int failures = 0;

#define CHECK(cond, msg)                                     \
  do {                                                       \
    if (!(cond)) {                                           \
      fprintf(stderr, "FAIL: %s\n", msg);                    \
      failures++;                                            \
    } else {                                                 \
      printf("PASS: %s\n", msg);                             \
    }                                                        \
  } while (0)

int main(void) {
  iwrc rc = iw_init();
  CHECK(rc == 0, "iw_init() returns 0");

  struct iwxstr *xs = iwxstr_new_printf("iowow-%d", 152);
  CHECK(xs != NULL, "iwxstr_new_printf allocates");

  rc = iwxstr_cat2(xs, "-ok");
  CHECK(rc == 0, "iwxstr_cat2 appends");

  const char *ptr = iwxstr_ptr(xs);
  CHECK(ptr != NULL, "iwxstr_ptr returns content");
  CHECK(strcmp(ptr, "iowow-152-ok") == 0, "content is 'iowow-152-ok'");

  size_t len = iwxstr_len(xs);
  CHECK(len == strlen("iowow-152-ok"), "length matches");

  /* 释放并持有指针再次校验（真实使用场景） */
  const char *keep = iwxstr_destroy_keep_ptr(xs);
  CHECK(keep != NULL && strcmp(keep, "iowow-152-ok") == 0, "destroy_keep_ptr preserves content");

  if (failures == 0) {
    printf("test_iowow: ALL PASS (iowow %s)\n", iowow_version_full());
    return 0;
  }
  fprintf(stderr, "test_iowow: %d failure(s)\n", failures);
  return 1;
}