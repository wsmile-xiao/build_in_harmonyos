/* test_package/test_receiver.c — librist receiver 与地址解析测试（R34 实质测试）。
 *
 * 真实调用 librist API：receiver 上下文创建、rist_parse_address2
 * URL 解析、peer 配置释放与销毁。仅解析不建连，不占用端口，
 * 沙箱与真机均可运行。
 */
#include <stdio.h>
#include <librist/librist.h>

int main(void)
{
    struct rist_ctx *ctx = NULL;
    struct rist_logging_settings log = LOGGING_SETTINGS_INITIALIZER;
    struct rist_logging_settings *log_ptr = &log;

    if (rist_logging_set(&log_ptr, RIST_LOG_ERROR,
                         NULL, NULL, NULL, NULL) < 0) {
        printf("FAIL: rist_logging_set\n");
        return 1;
    }

    if (rist_receiver_create(&ctx, RIST_PROFILE_MAIN, &log) != 0 ||
        ctx == NULL) {
        printf("FAIL: rist_receiver_create\n");
        return 1;
    }
    printf("PASS: receiver context created\n");

    struct rist_peer_config *cfg = NULL;
    if (rist_parse_address2("rist://@127.0.0.1:19680", &cfg) != 0 ||
        cfg == NULL) {
        printf("FAIL: rist_parse_address2\n");
        rist_destroy(ctx);
        return 1;
    }
    printf("PASS: parsed rist url\n");

    rist_peer_config_free2(&cfg);
    rist_destroy(ctx);
    printf("PASS: receiver lifecycle OK\n");
    return 0;
}
