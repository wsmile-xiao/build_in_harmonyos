#include <stdio.h>
#include <stdlib.h>
#include <ndp.h>

/* R34: 真实消费者验证 —— 实际调用 libndp 公开 API 并断言语义，而非仅打印。
 *
 * 说明：ndp_open() 内部会创建 raw ICMPv6 socket（SOCK_RAW，需 root/特权能力），
 * 在 CI 沙箱/非特权环境下必然 EACCES 失败，故不作为消费者测试入口。
 * 这里改用无需特权的消息 API（libndp 公开接口的真实调用）：
 *   1. ndp_msg_new(NDP_MSG_RS)  —— 分配并初始化 RS 消息，应返回 0；
 *   2. ndp_msg_new(NDP_MSG_ALL) —— 非法类型，应返回负值（-EINVAL 语义）；
 *   3. ndp_msg_destroy()        —— 释放，验证生命周期配对。
 */
int main(void) {
    struct ndp_msg *msg = NULL;

    if (ndp_msg_new(&msg, NDP_MSG_RS) != 0 || msg == NULL) {
        fprintf(stderr, "test libndp 1.9: ndp_msg_new(RS) FAILED\n");
        return 1;
    }
    ndp_msg_destroy(msg);

    if (ndp_msg_new(&msg, NDP_MSG_ALL) == 0) {
        fprintf(stderr, "test libndp 1.9: ndp_msg_new(NDP_MSG_ALL) should fail\n");
        ndp_msg_destroy(msg);
        return 1;
    }

    printf("test libndp 1.9: ndp_msg_new/destroy OK\n");
    return 0;
}
