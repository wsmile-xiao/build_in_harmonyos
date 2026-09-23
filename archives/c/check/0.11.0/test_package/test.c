/* test_package/test.c — check 0.11.0 消费者用例（HarmonyOS 专项）。

   仅使用 check 已安装/导出的公开头文件与公开 API：
   suite_create / tcase_create / suite_add_tcase / tcase_add_test /
   tcase_add_unchecked_fixture / srunner_create / srunner_run_all /
   srunner_ntests_failed / srunner_free，以及断言宏 ck_assert / ck_assert_int_eq。

   实际编译、链接、运行一个完整测试套件并断言可观察结果（失败数==0），
   验证第三方消费者在 OHOS 上可正常使用 check 框架。

   注意：check 的 srunner 默认 fork 模式依赖可写临时目录建立消息通道
   （check_msg.c open_tmp_file → tmpfile/mkstemp）。本用例【不】硬编码任何
   执行端绝对路径：TMPDIR/TMP/TEMP 由 test_package/conanfile.py 的 test()
   动态创建可写目录并注入（修复远端 CI 上执行端本机路径不存在导致的
   "No messaging setup" 失败，R02 返工）。
*/
#include <check.h>
#include <stdio.h>

static int fixture_val = 0;

static void fix_setup(void)
{
    fixture_val = 42;
}

START_TEST(test_public_api_add)
{
    ck_assert_int_eq(fixture_val, 42);
    ck_assert_int_eq(1 + 1, 2);
}
END_TEST

START_TEST(test_public_api_sub)
{
    ck_assert_int_eq(3 - 1, 2);
    ck_assert(10 > 3);
}
END_TEST

int main(void)
{
    Suite *s = suite_create("ConsumerSuite");
    if (!s) {
        fprintf(stderr, "FAIL: suite_create returned NULL\n");
        return 1;
    }
    TCase *tc = tcase_create("ConsumerTC");
    if (!tc) {
        fprintf(stderr, "FAIL: tcase_create returned NULL\n");
        return 1;
    }
    tcase_add_unchecked_fixture(tc, fix_setup, NULL);
    tcase_add_test(tc, test_public_api_add);
    tcase_add_test(tc, test_public_api_sub);
    suite_add_tcase(s, tc);

    SRunner *sr = srunner_create(s);
    if (!sr) {
        fprintf(stderr, "FAIL: srunner_create returned NULL\n");
        return 1;
    }
    srunner_run_all(sr, CK_SILENT);
    int failed = srunner_ntests_failed(sr);
    srunner_free(sr);

    if (failed != 0) {
        fprintf(stderr, "FAIL: %d checks failed\n", failed);
        return 1;
    }
    printf("check consumer test: PASS (2 assertions, 0 failures)\n");
    return 0;
}