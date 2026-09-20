/*
 * Ceedling 生成 runner 的最小替代：test/test_common_func.c 只依赖 unity.h 与
 * tusb_common.h，不含 CMock 生成的 mock_*，因此不需要 Ruby/Ceedling 就能跑。
 * 用例函数与 setUp/tearDown 全部由上游 test_common_func.c 提供，本文件只补 main。
 */

#include "unity.h"

void setUp(void);
void tearDown(void);

void test_TU_ARGS_NUM(void);

int main(void)
{
  UNITY_BEGIN();
  RUN_TEST(test_TU_ARGS_NUM);
  return UNITY_END();
}
