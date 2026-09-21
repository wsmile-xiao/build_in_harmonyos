/* test.c — libdex test_package 消费者测试
 *
 * 验证 libdex 安装产物可被第三方程序编译、链接、调用并正常运行：
 *   - 仅通过已安装的公开头文件 <libdex.h> 与公开 API 使用 libdex
 *   - 调用 dex_init / dex_scheduler_spawn / dex_future_get_status /
 *     dex_future_get_value 等公开 API
 *   - 覆盖 fiber 调度（依赖 libucontext 的 OHOS 适配点）并有可观察结果
 */

#include <glib.h>
#include <libdex.h>
static int ran = 0;

static DexFuture *
consumer_fiber_func (gpointer user_data)
{
  ran = 7;
  return dex_future_new_for_int (7);
}

int
main (void)
{
  DexScheduler *scheduler;
  DexFuture *future;
  const GValue *value;

  dex_init ();

  /* 公开 API：获取默认调度器并 spawn 一个 fiber */
  scheduler = dex_scheduler_get_default ();
  g_assert_nonnull (scheduler);

  future = dex_scheduler_spawn (scheduler, 0, consumer_fiber_func, NULL, NULL);
  g_assert_nonnull (future);

  /* P3-① 修复：等待 fiber 完成（完成标志 + 空转迭代 + 超时上限）。
   * 原 g_main_context_pending 在 pending 源为空时提前返回，存在
   * fiber 尚未运行即退出检查的偶发竞态；改为显式等待 ran 标志置位，
   * 期间持续非阻塞迭代驱动调度，并设 5s 超时兜底防死循环。 */
  {
    gint64 deadline_ms = g_get_monotonic_time () / 1000 + 5000;
    while (ran != 7 && (g_get_monotonic_time () / 1000) < deadline_ms)
      {
        g_main_context_iteration (NULL, FALSE);
        g_usleep (1000);
      }
  }

  /* 公开 API：读取 future 状态与结果值 */
  if (dex_future_get_status (future) != DEX_FUTURE_STATUS_RESOLVED)
    {
      g_printerr ("test_libdex: future not resolved\n");
      return 1;
    }
  if (ran != 7)
    {
      g_printerr ("test_libdex: fiber callback did not run\n");
      return 1;
    }
  value = dex_future_get_value (future, NULL);
  if (value == NULL)
    {
      g_printerr ("test_libdex: future value unavailable\n");
      return 1;
    }
  if (g_value_get_int (value) != 7)
    {
      g_printerr ("test_libdex: unexpected value %d\n", g_value_get_int (value));
      return 1;
    }

  g_print ("test_libdex: PASSED (fiber value=%d)\n", g_value_get_int (value));
  dex_unref (future);
  return 0;
}