/* SPDX-License-Identifier: MIT */
/* libei 消费者测试 — 真实调用 libei/libeis 公共 API。
 *
 * 验证点：
 * 1. libei 客户端上下文生命周期（ei_new_sender/ei_ref/ei_unref）
 * 2. ei_is_sender/ei_get_user_data 语义
 * 3. libeis 服务端上下文生命周期（eis_new/eis_unref）
 * 4. 链接产物存在（libei.so + libeis.so，运行即验证）
 *
 * 不依赖 socket 环境（OHOS 沙箱内无 EIS 服务端），覆盖无 IO 的
 * 公共 API 面。
 */
#include <stdio.h>
#include <string.h>

#include <libei.h>
#include <libeis.h>

int main(void)
{
    int rc = 0;

    /* ── libei 客户端 ─────────────────────────────────────── */
    static char user_data[] = "ohos-libei-test";
    struct ei *ei = ei_new_sender(user_data);
    if (ei == NULL) {
        fprintf(stderr, "FAIL: ei_new_sender() returned NULL\n");
        return 1;
    }
    printf("ei context created: %p\n", (void *)ei);

    if (!ei_is_sender(ei)) {
        fprintf(stderr, "FAIL: ei_is_sender() false for sender context\n");
        rc = 1;
    } else {
        printf("ei_is_sender: true\n");
    }

    char *ud = ei_get_user_data(ei);
    if (ud != user_data || strcmp(ud, "ohos-libei-test") != 0) {
        fprintf(stderr, "FAIL: ei_get_user_data() mismatch: %p\n", (void *)ud);
        rc = 1;
    } else {
        printf("ei_get_user_data: ok\n");
    }

    struct ei *ref = ei_ref(ei);
    if (ref != ei) {
        fprintf(stderr, "FAIL: ei_ref() returned different pointer\n");
        rc = 1;
    }
    ei_unref(ref);
    ei_unref(ei);
    printf("libei lifecycle: ok\n");

    /* ── libeis 服务端 ────────────────────────────────────── */
    struct eis *eis = eis_new(user_data);
    if (eis == NULL) {
        fprintf(stderr, "FAIL: eis_new() returned NULL\n");
        return 1;
    }
    printf("eis context created: %p\n", (void *)eis);
    eis_unref(eis);
    printf("libeis lifecycle: ok\n");

    if (rc == 0)
        printf("libei test_package: PASS\n");
    return rc;
}
