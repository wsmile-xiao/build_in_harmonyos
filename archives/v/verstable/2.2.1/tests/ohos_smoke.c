/* HarmonyOS 专项测试 — verstable 2.2.1
 *
 * 目的: 验证 verstable 公开 API 在 HarmonyOS PC (aarch64) 平台上，
 * 使用 OHOS SDK clang 15 工具链 + libc++ 实际编译、链接并运行正常。
 * 用例内容: 实例化 int set 与 int->int map，插入/擦除/检索/迭代，
 * 并断言可观察结果（与 test_package 消费者测试互补，非复述）。
 *
 * 编译（OHOS 工具链）:
 *   clang -std=c11 -O2 -Wall -I<include> ohos_smoke.c -o ohos_smoke
 * 运行:
 *   ./ohos_smoke
 */
#include <stdio.h>
#include <stdlib.h>

#define NAME int_set
#define KEY_TY int
#include "verstable.h"

#define NAME int_int_map
#define KEY_TY int
#define VAL_TY int
#include "verstable.h"

int main(void)
{
  /* --- Set: 5000 个键的批量插入/擦除/检索 --- */
  int_set our_set;
  vt_init(&our_set);

  for (int i = 0; i < 5000; ++i)
  {
    int_set_itr itr = vt_insert(&our_set, i);
    if (vt_is_end(itr)) { vt_cleanup(&our_set); return 1; }
  }
  if (vt_size(&our_set) != 5000)
  {
    fprintf(stderr, "FAIL: set size %zu != 5000\n", vt_size(&our_set));
    vt_cleanup(&our_set);
    return 1;
  }
  /* 擦除偶数键 */
  for (int i = 0; i < 5000; i += 2)
    vt_erase(&our_set, i);
  if (vt_size(&our_set) != 2500)
  {
    fprintf(stderr, "FAIL: set size after erase %zu != 2500\n", vt_size(&our_set));
    vt_cleanup(&our_set);
    return 1;
  }
  /* 检索: 奇数键在，偶数键不在 */
  for (int i = 0; i < 5000; ++i)
  {
    int_set_itr itr = vt_get(&our_set, i);
    int expect_present = (i % 2 == 1);
    int present = !vt_is_end(itr);
    if (present != expect_present)
    {
      fprintf(stderr, "FAIL: key %d present=%d expect=%d\n", i, present, expect_present);
      vt_cleanup(&our_set);
      return 1;
    }
  }
  /* 迭代计数必须等于当前 size */
  size_t iter_count = 0;
  for (int_set_itr itr = vt_first(&our_set); !vt_is_end(itr); itr = vt_next(itr))
    ++iter_count;
  if (iter_count != vt_size(&our_set))
  {
    fprintf(stderr, "FAIL: iter_count %zu != size %zu\n", iter_count, vt_size(&our_set));
    vt_cleanup(&our_set);
    return 1;
  }
  vt_cleanup(&our_set);

  /* --- Map: 键值对插入与读取 --- */
  int_int_map our_map;
  vt_init(&our_map);

  for (int i = 0; i < 10000; ++i)
  {
    int_int_map_itr itr = vt_insert(&our_map, i, i * 3);
    if (vt_is_end(itr)) { vt_cleanup(&our_map); return 1; }
  }
  size_t map_size = vt_size(&our_map);
  if (map_size != 10000)
  {
    fprintf(stderr, "FAIL: map size %zu != 10000\n", map_size);
    vt_cleanup(&our_map);
    return 1;
  }
  /* 校验值映射 */
  for (int i = 0; i < 10000; ++i)
  {
    int_int_map_itr itr = vt_get(&our_map, i);
    if (vt_is_end(itr) || itr.data->val != i * 3)
    {
      fprintf(stderr, "FAIL: map get %d -> %d (expect %d)\n", i,
              vt_is_end(itr) ? -1 : itr.data->val, i * 3);
      vt_cleanup(&our_map);
      return 1;
    }
  }
  vt_cleanup(&our_map);

  printf("OHOS smoke test: PASS (set 5000 keys/2500 remain, map 10000 pairs verified)\n");
  return 0;
}