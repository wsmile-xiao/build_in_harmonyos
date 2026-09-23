/*
 * test_ohos.c — libok 0.6.5 鸿蒙特有测试（r02 新增）
 *
 * 在 OHOS arm64 目标上编译、链接并运行 libok（仅使用公开头文件 ok.h 与
 * 公开 API：ok_expect/ok/notok/ok_done/ok_count/ok_reset），通过管道捕获
 * stdout 后程序化校验以下可观察鸿蒙行为：
 *   1) TAP 计划行（ok_expect 的 "1..N"）与 TAP 版本头实际输出；
 *   2) ok() 断言计数与 ok_done() 汇总（成功路径返回 true）；
 *   3) notok 失败路径使 ok_done() 返回 false（失败检测语义）；
 *   4) 输出含 "# pass" / "# fail" 汇总行——验证真实运行时输出而非空壳。
 *
 * 与上游 test.c（仅跑 TAP 冒烟）和 test_package 消费者 test_libok
 * （2×ok + ok_done）不同：本测试对捕获的输出内容做字符串级断言，
 * 独立计数，验证鸿蒙目标上 libok 输出管线的完整性。
 *
 * 构建/运行由 test_package/CMakeLists.txt 注册（conan create 自动执行）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "ok.h"

int main(void) {
  char buf[8192];
  int pfd[2];
  int saved = -1;
  ssize_t n = 0;

  if (pipe(pfd) != 0) {
    fprintf(stderr, "OHOS-SPECIAL-TEST FAIL: pipe() failed\n");
    return 1;
  }
  saved = dup(1);
  if (saved < 0 || dup2(pfd[1], 1) < 0) {
    fprintf(stderr, "OHOS-SPECIAL-TEST FAIL: dup/dup2 failed\n");
    return 1;
  }
  close(pfd[1]);
  fflush(stdout);

  /* 成功路径：期望 3 个 ok，ok_done() 应返回 true */
  ok_expect(3);
  ok("alpha");
  ok("beta");
  ok("gamma");
  int ok_done_ok = ok_done();

  /* 失败路径：reset 后 1 ok + 1 notok，ok_done() 应返回 false */
  ok_reset();
  ok("first");
  notok("oops");
  int ok_done_fail = ok_done();

  fflush(stdout);
  dup2(saved, 1);
  close(saved);
  n = read(pfd[0], buf, sizeof(buf) - 1);
  close(pfd[0]);
  if (n < 0) n = 0;
  buf[n] = '\0';

  int pass = 1;
  if (!ok_done_ok) {
    fprintf(stderr, "FAIL: ok_done() after 3 ok != true\n");
    pass = 0;
  }
  if (ok_done_fail) {
    fprintf(stderr, "FAIL: ok_done() after notok != false\n");
    pass = 0;
  }
  if (strstr(buf, "TAP version 14") == NULL) {
    fprintf(stderr, "FAIL: missing TAP version header in output\n");
    pass = 0;
  }
  if (strstr(buf, "1..3") == NULL) {
    fprintf(stderr, "FAIL: missing ok_expect plan '1..3' in output\n");
    pass = 0;
  }
  if (strstr(buf, "ok 1 - alpha") == NULL ||
      strstr(buf, "ok 3 - gamma") == NULL) {
    fprintf(stderr, "FAIL: missing ok lines in output\n");
    pass = 0;
  }
  if (strstr(buf, "not ok") == NULL) {
    fprintf(stderr, "FAIL: missing not ok line in output\n");
    pass = 0;
  }
  if (strstr(buf, "# pass") == NULL || strstr(buf, "# fail") == NULL) {
    fprintf(stderr, "FAIL: missing TAP summary lines in output\n");
    pass = 0;
  }

  if (pass) {
    printf("OHOS-SPECIAL-TEST PASS\n");
    return 0;
  }
  printf("OHOS-SPECIAL-TEST FAIL\n--- captured output ---\n%s\n", buf);
  return 1;
}
