/* test_package/test.c — Check 消费者测试
   验证可链接并使用 Check API（不依赖临时文件的轻量 API）。
   suite_create/srunner_free 是公开 API，无需临时文件 IPC，
   可在 OHOS 沙箱中安全运行。
*/

#include <check.h>
#include <stdio.h>

int main(void) {
    Suite *s = suite_create("Smoke");
    if (!s) {
        fprintf(stderr, "FAIL: suite_create returned NULL\n");
        return 1;
    }
    TCase *tc = tcase_create("Core");
    if (!tc) {
        fprintf(stderr, "FAIL: tcase_create returned NULL\n");
        /* suite freed via process exit — suite_free not a public API */
        return 1;
    }
    suite_add_tcase(s, tc);
    SRunner *sr = srunner_create(s);
    if (!sr) {
        fprintf(stderr, "FAIL: srunner_create returned NULL\n");
        return 1;
    }
    srunner_free(sr);
    printf("check smoke test: PASS\n");
    return 0;
}
