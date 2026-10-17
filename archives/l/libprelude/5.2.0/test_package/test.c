/*
 * libprelude 5.2.0 消费者冒烟测试（Conan test_package / L1）。
 *
 * 只使用 libprelude 的公开 API，验证：
 *   1. 头文件与 pkg-config/CMake 集成（能 #include <prelude.h> 并链上 libprelude.so）
 *   2. prelude_string_* 字符串对象的分配 / 追加 / 取值 / 销毁
 *   3. IDMEF 对象树 Message → Alert → CreateTime（含时间戳合理性）
 * 任何一条不满足都以非 0 退出，让 conan create / CI 直接失败。
 */
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <prelude.h>

static int failures;

#define CHECK(cond, ...)                                                       \
        do {                                                                   \
                if (!(cond)) {                                                 \
                        failures++;                                            \
                        fprintf(stderr, "FAIL " __VA_ARGS__);                  \
                        fprintf(stderr, "  [%s:%d]\n", __FILE__, __LINE__);    \
                }                                                              \
        } while (0)

static void test_prelude_string(void)
{
        prelude_string_t *str = NULL;

        CHECK(prelude_string_new_dup(&str, "prelude") == 0, "prelude_string_new_dup");
        if (str == NULL) {
                return;
        }
        /* prelude_string_cat 返回追加的字节数（上游 tests/prelude-string.c 也按
         * ">= 0" 断言），不是 0/非 0 错误码 */
        CHECK(prelude_string_cat(str, "-harmonyos") >= 0, "prelude_string_cat");
        CHECK(prelude_string_get_len(str) == strlen("prelude-harmonyos"),
              "prelude_string_get_len = %zu", prelude_string_get_len(str));
        CHECK(strcmp(prelude_string_get_string_or_default(str, "<null>"),
                     "prelude-harmonyos") == 0,
              "prelude_string content = %s",
              prelude_string_get_string_or_default(str, "<null>"));
        prelude_string_destroy(str);
}

static void test_idmef_message(void)
{
        idmef_message_t *message = NULL;
        idmef_alert_t *alert = NULL;
        idmef_time_t *create_time;
        time_t now;

        CHECK(idmef_message_new(&message) == 0, "idmef_message_new");
        if (message == NULL) {
                return;
        }
        CHECK(idmef_message_new_alert(message, &alert) == 0, "idmef_message_new_alert");
        if (alert != NULL) {
                create_time = idmef_alert_get_create_time(alert);
                CHECK(create_time != NULL, "idmef_alert_get_create_time returned NULL");
                if (create_time != NULL) {
                        now = time(NULL);
                        CHECK((long) now - (long) idmef_time_get_sec(create_time) < 60,
                              "alert create time %u is far from now %ld",
                              idmef_time_get_sec(create_time), (long) now);
                }
        }
        idmef_message_destroy(message);
}

int main(void)
{
        CHECK(strcmp(LIBPRELUDE_VERSION, "5.2.0") == 0,
              "LIBPRELUDE_VERSION = %s", LIBPRELUDE_VERSION);
        test_prelude_string();
        test_idmef_message();

        if (failures != 0) {
                fprintf(stderr, "libprelude consumer test: %d assertion(s) failed\n", failures);
                return 1;
        }
        printf("libprelude %s consumer test: OK\n", LIBPRELUDE_VERSION);
        return 0;
}
