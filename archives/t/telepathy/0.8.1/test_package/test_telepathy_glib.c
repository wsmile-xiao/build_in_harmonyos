/* test_telepathy_glib.c — telepathy-glib 0.8.1 消费者测试（R34 真实产物 + API 调用）。
 *
 * 说明：0.8.1（2009）没有聚合头 telepathy-glib.h，公开 API 按模块分头文件，
 * 故逐个 include；enums.h 内部 include <telepathy-glib/_gen/telepathy-enums.h>，
 * 一并验证 glib-mkenums 生成的 _gen 头已被正确打包。
 */
#include <telepathy-glib/util.h>
#include <telepathy-glib/errors.h>
#include <telepathy-glib/enums.h>
#include <glib.h>
#include <stdio.h>

int
main (void)
{
  GValue *v = NULL;
  GQuark quark = 0;
  const gchar *quark_str = NULL;

  /* util：GValue 值构造（纯函数，不依赖运行环境） */
  v = tp_g_value_slice_new_boolean (TRUE);
  if (v == NULL)
    {
      fprintf (stderr, "FAIL: tp_g_value_slice_new_boolean returned NULL\n");
      return 1;
    }
  if (!G_VALUE_HOLDS_BOOLEAN (v) || g_value_get_boolean (v) != TRUE)
    {
      fprintf (stderr, "FAIL: GValue 内容不正确\n");
      return 1;
    }
  tp_g_value_slice_free (v);

  /* util：字符串比较辅助（TRUE 表示不同） */
  if (tp_strdiff ("abc", "abc") || !tp_strdiff ("abc", "abd"))
    {
      fprintf (stderr, "FAIL: tp_strdiff 行为异常\n");
      return 1;
    }

  /* errors：错误域 quark 注册。
   * 注意：制品仓的 glib 是静态库，libtelepathy-glib.so 会内嵌一份 glib；消费者若
   * 也静态链接 glib，两份 glib 的 GType（glib ≥2.80 的索引随机化）/GQuark 运行期
   * 状态天然隔离，跨模块用 g_quark_to_string() 反查会失败。故此处只校验同副本内的
   * 非零值与稳定性（详见 notes.md「平台限制」）。
   */
  quark = tp_errors_quark ();
  if (quark == 0)
    {
      fprintf (stderr, "FAIL: tp_errors_quark returned 0\n");
      return 1;
    }
  if (tp_errors_quark () != quark)
    {
      fprintf (stderr, "FAIL: tp_errors_quark 返回值不稳定\n");
      return 1;
    }
  quark_str = g_quark_to_string (quark);
  (void) quark_str;

  printf ("OK: telepathy-glib link + util/error API callable\n");
  return 0;
}
