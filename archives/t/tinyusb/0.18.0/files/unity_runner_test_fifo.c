/*
 * Ceedling 生成 runner 的最小替代：test/test_fifo.c 只依赖 unity.h、osal/osal.h
 * 与 tusb_fifo.h，使用真实的 tu_fifo 实现而非 mock，因此不需要 Ruby/Ceedling。
 * 用例函数与 setUp/tearDown 全部由上游 test_fifo.c 提供，本文件只补 main。
 */

#include "unity.h"

void setUp(void);
void tearDown(void);

void test_normal(void);
void test_item_size(void);
void test_read_n(void);
void test_write_n(void);
void test_write_double_overflowed(void);
void test_write_overwritable2(void);
void test_peek(void);
void test_get_read_info_when_no_wrap(void);
void test_get_read_info_when_wrapped(void);
void test_get_write_info_when_no_wrap(void);
void test_get_write_info_when_wrapped(void);
void test_empty(void);
void test_full(void);
void test_rd_idx_wrap(void);

int main(void)
{
  UNITY_BEGIN();
  RUN_TEST(test_normal);
  RUN_TEST(test_item_size);
  RUN_TEST(test_read_n);
  RUN_TEST(test_write_n);
  RUN_TEST(test_write_double_overflowed);
  RUN_TEST(test_write_overwritable2);
  RUN_TEST(test_peek);
  RUN_TEST(test_get_read_info_when_no_wrap);
  RUN_TEST(test_get_read_info_when_wrapped);
  RUN_TEST(test_get_write_info_when_no_wrap);
  RUN_TEST(test_get_write_info_when_wrapped);
  RUN_TEST(test_empty);
  RUN_TEST(test_full);
  RUN_TEST(test_rd_idx_wrap);
  return UNITY_END();
}
