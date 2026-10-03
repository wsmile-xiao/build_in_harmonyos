/* test_package/test_jobrep.c — lcmaps-plugins-jobrep 1.5.8 consumer test (L1)

 * 真实调用插件导出的 LCMAPS 入口点（R34：禁止只打印字符串的空壳测试）。
 * 插件的五个入口点声明于 <lcmaps/lcmaps_plugin_prototypes.h>，由宿主 LCMAPS
 * 进程在运行时加载后调用；本测试直接链接 liblcmaps_jobrep 并调用其中三个
 * 不依赖数据库连接的入口点，逐项断言其返回值与输出：
 *
 *   1. plugin_initialize() —— 参数解析与前置校验
 *        · 未知参数        → LCMAPS_MOD_FAIL (1)
 *        · 缺少 --dsn      → LCMAPS_MOD_FAIL (1)
 *        · --dsn/--username → LCMAPS_MOD_SUCCESS (0)
 *        · --test 开关      → LCMAPS_MOD_SUCCESS (0)
 *   2. plugin_introspect() —— 回填 LCMAPS 参数表
 *        · 返回 LCMAPS_MOD_SUCCESS
 *        · argc == 3（user_dn / px509_chain / job_request，NULL 结尾）
 *        · argv 非空且首/末条目名正确
 *   3. plugin_terminate() —— 释放内部配置，返回 LCMAPS_MOD_SUCCESS
 *
 * 不调用 plugin_run()/plugin_verify()：二者需要可用的 ODBC 数据源与
 * X.509 凭证链，属环境依赖，不纳入离线消费者测试。
 *
 * 任一断言失败即 return 1，使 conan create 失败。
 */
#include <lcmaps/lcmaps_plugin_prototypes.h>
#include <lcmaps/lcmaps_arguments.h>
#include <lcmaps/lcmaps_defines.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;

static void check(int cond, const char *what)
{
    if (cond) {
        printf("  [ok]   %s\n", what);
    } else {
        printf("  [FAIL] %s\n", what);
        failures++;
    }
}

int main(void)
{
    int rc;
    int argc;
    lcmaps_argument_t *argv = NULL;

    printf("lcmaps-plugins-jobrep consumer test — LCMAPS plugin API\n");

    /* ── 1. plugin_initialize(): 未知参数必须被拒绝 ── */
    {
        char *bad_argv[] = { (char *)"jobrep", (char *)"--no-such-option", NULL };
        rc = plugin_initialize(2, bad_argv);
        check(rc == LCMAPS_MOD_FAIL,
              "plugin_initialize() rejects an unknown option (LCMAPS_MOD_FAIL)");
    }

    /* ── 2. plugin_initialize(): 缺少 --dsn 必须失败 ── */
    {
        char *nodsn_argv[] = { (char *)"jobrep", NULL };
        rc = plugin_initialize(1, nodsn_argv);
        check(rc == LCMAPS_MOD_FAIL,
              "plugin_initialize() fails without --dsn (LCMAPS_MOD_FAIL)");
    }

    /* ── 3. plugin_initialize(): 提供 --dsn/--username 后成功 ── */
    {
        char *good_argv[] = {
            (char *)"jobrep",
            (char *)"--dsn",      (char *)"jobrep_consumer_test_dsn",
            (char *)"--username", (char *)"jobrep_consumer_test_user",
            NULL
        };
        rc = plugin_initialize(5, good_argv);
        check(rc == LCMAPS_MOD_SUCCESS,
              "plugin_initialize() accepts --dsn/--username (LCMAPS_MOD_SUCCESS)");
    }

    /* ── 4. plugin_initialize(): --test 开关被识别 ── */
    {
        /* 6 个实参：jobrep / --test / --dsn dsn / --username user
           （argc 必须与实参个数一致，否则尾部参数扫不到） */
        char *test_argv[] = {
            (char *)"jobrep",
            (char *)"--test",
            (char *)"--dsn",      (char *)"jobrep_consumer_test_dsn",
            (char *)"--username", (char *)"jobrep_consumer_test_user",
            NULL
        };
        rc = plugin_initialize(6, test_argv);
        check(rc == LCMAPS_MOD_SUCCESS,
              "plugin_initialize() recognises the --test switch");
    }

    /* ── 5-9. plugin_introspect(): 回填参数表 ── */
    argc = -1;
    argv = NULL;
    rc = plugin_introspect(&argc, &argv);
    check(rc == LCMAPS_MOD_SUCCESS,
          "plugin_introspect() returns LCMAPS_MOD_SUCCESS");
    check(argc == 3,
          "plugin_introspect() reports 3 arguments (user_dn/px509_chain/job_request)");
    check(argv != NULL,
          "plugin_introspect() fills the argument pointer");
    check(argv != NULL && argv[0].argName != NULL
              && strcmp(argv[0].argName, "user_dn") == 0,
          "plugin_introspect() first argument is \"user_dn\"");
    check(argv != NULL && argv[2].argName != NULL
              && strcmp(argv[2].argName, "job_request") == 0,
          "plugin_introspect() third argument is \"job_request\"");

    /* ── 10. plugin_terminate(): 正常收尾 ── */
    rc = plugin_terminate();
    check(rc == LCMAPS_MOD_SUCCESS,
          "plugin_terminate() returns LCMAPS_MOD_SUCCESS");

    if (failures != 0) {
        printf("test lcmaps-plugins-jobrep 1.5.8: FAIL (%d assertion(s) failed)\n",
               failures);
        return 1;
    }
    printf("test lcmaps-plugins-jobrep 1.5.8: OK (10/10 assertions passed)\n");
    return 0;
}
