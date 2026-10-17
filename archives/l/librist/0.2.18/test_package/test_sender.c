/* test_package/test_sender.c — librist sender 生命周期测试（R34 实质测试）。
 *
 * 真实调用 librist API：版本查询、日志初始化、sender 上下文创建与销毁。
 * 任一环节失败返回非零，conan create 即失败。不绑定/连接任何 socket，
 * 沙箱与真机均可运行。
 */
#include <stdio.h>
#include <librist/librist.h>

int main(void)
{
    const char *ver = librist_version();
    const char *api = librist_api_version();

    if (ver == NULL || api == NULL) {
        printf("FAIL: librist_version/api_version returned NULL\n");
        return 1;
    }
    printf("librist version: %s, api: %s\n", ver, api);

    struct rist_ctx *ctx = NULL;
    struct rist_logging_settings log = LOGGING_SETTINGS_INITIALIZER;
    struct rist_logging_settings *log_ptr = &log;

    if (rist_logging_set(&log_ptr, RIST_LOG_ERROR,
                         NULL, NULL, NULL, NULL) < 0) {
        printf("FAIL: rist_logging_set\n");
        return 1;
    }

    if (rist_sender_create(&ctx, RIST_PROFILE_MAIN, 0, &log) != 0 ||
        ctx == NULL) {
        printf("FAIL: rist_sender_create\n");
        return 1;
    }
    printf("PASS: sender context created\n");

    rist_destroy(ctx);
    printf("PASS: sender lifecycle OK\n");
    return 0;
}
