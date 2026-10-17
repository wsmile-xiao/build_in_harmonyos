#include <libmalcontent/malcontent.h>

#include <glib.h>

/* test_package 消费者验证：真实调用 libmalcontent 核心 API。
 * 全部为纯内存操作（builder/serialize/deserialize），不依赖 D-Bus 会话总线，
 * 可在 OHOS 上完整运行。 */
int
main (int argc, char **argv)
{
  g_autoptr(MctAppFilterBuilder) app_filter_builder = NULL;
  g_autoptr(MctAppFilter) app_filter = NULL;
  g_autoptr(MctAppFilter) app_filter_copy = NULL;
  g_autoptr(GVariant) serialized = NULL;
  g_autoptr(GError) local_error = NULL;
  g_autoptr(MctSessionLimitsBuilder) session_limits_builder = NULL;
  g_autoptr(MctSessionLimits) session_limits = NULL;
  g_autoptr(GVariant) session_serialized = NULL;

  /* 1. AppFilter builder → filter */
  app_filter_builder = mct_app_filter_builder_new ();
  g_assert_nonnull (app_filter_builder);
  mct_app_filter_builder_blocklist_path (app_filter_builder, "/usr/bin/game");
  mct_app_filter_builder_set_oars_value (app_filter_builder, "violence-fantasy",
                                         MCT_APP_FILTER_OARS_VALUE_INTENSE);
  mct_app_filter_builder_set_allow_system_installation (app_filter_builder, FALSE);
  app_filter = mct_app_filter_builder_end (app_filter_builder);
  g_assert_nonnull (app_filter);

  /* 2. 查询 API 实质断言 */
  g_assert_true (mct_app_filter_is_enabled (app_filter));
  g_assert_false (mct_app_filter_is_path_allowed (app_filter, "/usr/bin/game"));
  g_assert_true (mct_app_filter_is_path_allowed (app_filter, "/usr/bin/editor"));
  g_assert_cmpint (mct_app_filter_get_oars_value (app_filter, "violence-fantasy"),
                   ==, MCT_APP_FILTER_OARS_VALUE_INTENSE);
  g_assert_false (mct_app_filter_is_system_installation_allowed (app_filter));

  /* 3. serialize → deserialize 往返（builder_end 默认 user_id=-1，保持一致） */
  serialized = mct_app_filter_serialize (app_filter);
  g_assert_nonnull (serialized);
  app_filter_copy = mct_app_filter_deserialize (serialized, (uid_t) -1, &local_error);
  g_assert_no_error (local_error);
  g_assert_nonnull (app_filter_copy);
  g_assert_true (mct_app_filter_equal (app_filter, app_filter_copy));
  g_assert_false (mct_app_filter_is_path_allowed (app_filter_copy, "/usr/bin/game"));

  /* 4. SessionLimits builder → serialize 往返 */
  session_limits_builder = mct_session_limits_builder_new ();
  g_assert_nonnull (session_limits_builder);
  mct_session_limits_builder_set_daily_schedule (session_limits_builder,
                                                 7 * 3600, 21 * 3600);
  session_limits = mct_session_limits_builder_end (session_limits_builder);
  g_assert_nonnull (session_limits);
  g_assert_true (mct_session_limits_is_enabled (session_limits));

  session_serialized = mct_session_limits_serialize (session_limits);
  g_assert_nonnull (session_serialized);

  /* 5. 基础类型检查 */
  g_assert_cmpuint (mct_app_filter_get_type (), !=, 0);
  g_assert_cmpuint (mct_session_limits_get_type (), !=, 0);

  g_print ("test_libmalcontent: all assertions passed\n");
  return 0;
}
