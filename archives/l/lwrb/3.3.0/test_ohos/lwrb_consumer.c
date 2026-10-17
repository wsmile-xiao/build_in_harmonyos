/*
 * test_ohos/lwrb_consumer.c — lwrb 3.3.0 HarmonyOS PC 专项消费者
 *
 * 仅通过已安装公开头文件 "lwrb/lwrb.h" 与公开 API 使用 lwrb：
 * lwrb_init / lwrb_is_ready / lwrb_write / lwrb_read / lwrb_reset /
 * lwrb_get_free / lwrb_get_full / lwrb_get_linear_block_write_address /
 * lwrb_get_linear_block_write_length / lwrb_advance。完成：
 *  1) 写入-读出往返与数据校验；
 *  2) 满/空状态机（容量 = size-1：写满后继续写被拒绝，reset 后恢复）；
 *  3) 线性块直接写入 + advance（业务常见 DMA 场景）。
 * 全部通过输出 "LWRB_OHOS_OK" 并以 0 退出。
 */
#include <stdio.h>
#include <string.h>

#include "lwrb/lwrb.h"

#define BUF_SIZE 16                    /* 容量上限 = 15（size-1 语义） */
#define PAYLOAD "lwrb-ohos"            /* 9 字节 */
#define FILL_PAYLOAD "0123456789ABCDE" /* 15 字节 = 容量上限 */

int
main(void) {
    lwrb_t buff;
    uint8_t storage[BUF_SIZE];
    uint8_t out[BUF_SIZE];

    memset(&buff, 0, sizeof(buff));
    memset(out, 0, sizeof(out));

    if (!lwrb_init(&buff, storage, sizeof(storage))) return 1;
    if (!lwrb_is_ready(&buff)) return 2;

    /* 1) 往返 */
    if (lwrb_write(&buff, PAYLOAD, sizeof(PAYLOAD) - 1) != sizeof(PAYLOAD) - 1) return 3;
    if (lwrb_get_full(&buff) != sizeof(PAYLOAD) - 1) return 4;
    if (lwrb_read(&buff, out, sizeof(PAYLOAD) - 1) != sizeof(PAYLOAD) - 1) return 5;
    if (memcmp(out, PAYLOAD, sizeof(PAYLOAD) - 1) != 0) return 6;
    if (lwrb_get_full(&buff) != 0) return 7;

    /* 2) 满/空状态机：容量 = size-1 */
    lwrb_reset(&buff);
    if (lwrb_get_free(&buff) != BUF_SIZE - 1) return 8;
    /* 填满：15 字节全部写入 */
    if (lwrb_write(&buff, FILL_PAYLOAD, BUF_SIZE - 1) != BUF_SIZE - 1) return 9;
    if (lwrb_get_full(&buff) != BUF_SIZE - 1) return 10;
    /* 已满：继续写入 1 字节必须被拒绝（返回 0） */
    if (lwrb_write(&buff, PAYLOAD, 1) != 0) return 11;
    lwrb_reset(&buff);
    if (lwrb_get_full(&buff) != 0) return 12;

    /* 3) 线性块直接写入 + advance（DMA 场景） */
    {
        void* dst = lwrb_get_linear_block_write_address(&buff);
        size_t wlen = lwrb_get_linear_block_write_length(&buff);
        if (dst == NULL || wlen < sizeof(PAYLOAD) - 1) return 13;
        memcpy(dst, PAYLOAD, sizeof(PAYLOAD) - 1);
        lwrb_advance(&buff, sizeof(PAYLOAD) - 1);
        if (lwrb_get_full(&buff) != sizeof(PAYLOAD) - 1) return 14;
        if (lwrb_read(&buff, out, sizeof(PAYLOAD) - 1) != sizeof(PAYLOAD) - 1) return 15;
        if (memcmp(out, PAYLOAD, sizeof(PAYLOAD) - 1) != 0) return 16;
    }

    printf("LWRB_OHOS_OK\n");
    return 0;
}