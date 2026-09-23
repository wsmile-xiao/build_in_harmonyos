/* test_package/test.c — libuv 1.52.1 (R34: 实质依赖被测包 API) */
#include <uv.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* 验证版本字符串 */
    const char *ver = uv_version_string();
    if (!ver) {
        fprintf(stderr, "uv_version_string() returned NULL\n");
        return 1;
    }
    printf("libuv version: %s\n", ver);

    /* 验证默认事件循环可创建 */
    uv_loop_t *loop = uv_default_loop();
    if (loop == NULL) {
        fprintf(stderr, "uv_default_loop() returned NULL\n");
        return 1;
    }

    /* 验证定时器可初始化 */
    uv_timer_t timer;
    int rc = uv_timer_init(loop, &timer);
    if (rc != 0) {
        fprintf(stderr, "uv_timer_init() failed: %s\n", uv_strerror(rc));
        return 1;
    }

    /* 验证循环可关闭 */
    rc = uv_loop_close(loop);
    if (rc != 0) {
        /* UV_EBUSY is acceptable if loop has active handles */
        fprintf(stderr, "uv_loop_close() returned: %s\n", uv_strerror(rc));
    }

    /* 验证 uv_os_get_passwd 可获取当前用户信息 */
    uv_passwd_t pwd;
    memset(&pwd, 0, sizeof(pwd));
    rc = uv_os_get_passwd(&pwd);
    if (rc != 0) {
        fprintf(stderr, "uv_os_get_passwd() failed: %s\n", uv_strerror(rc));
        return 1;
    }
    if (pwd.username == NULL || pwd.username[0] == '\0') {
        fprintf(stderr, "uv_os_get_passwd() returned empty username\n");
        uv_os_free_passwd(&pwd);
        return 1;
    }
    printf("os user: name=\"%s\" uid=%lu gid=%lu home=\"%s\"\n",
           pwd.username, (unsigned long)pwd.uid,
           (unsigned long)pwd.gid,
           pwd.homedir ? pwd.homedir : "(null)");
    uv_os_free_passwd(&pwd);

    printf("libuv test: all API calls passed\n");
    return 0;
}
