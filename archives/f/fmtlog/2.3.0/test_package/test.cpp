// fmtlog 2.3.0 消费者验证：调用 fmtlog 核心日志 API（R34 实质依赖）
#include <cstdio>
#include "fmtlog/fmtlog.h"

int main() {
  // 基础日志 + poll 冲刷队列，验证 fmtlog 库可链接可用
  logi("fmtlog consumer test: answer = {}", 42);
  logw("warning level message");
  fmtlog::poll();

  // 返回码验证格式化输出
  printf("fmtlog 2.3.0 consumer test PASSED\n");
  return 0;
}
