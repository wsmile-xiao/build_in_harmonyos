/*
 * test_package/test.c — lwrb 3.3.0 消费者验证
 *
 * 模拟业务上层组件：仅通过已安装的公开头文件 <lwrb/lwrb.h> 使用公开 API
 * （lwrb_init / lwrb_is_ready / lwrb_write / lwrb_get_full / lwrb_read），
 * 完成一次有业务意义的环形缓冲"写入 → 查询 → 读出 → 内容校验"往返，
 * 并输出可观察结果；任一环节失败返回非零退出码。
 *
 * 注意：lwrb 的容量语义是 size-1（读写指针需要在满/空之间留出区分位），
 * 故 64 字节缓冲最多容纳 63 字节数据；本用例的 32 字节载荷在容量内。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lwrb/lwrb.h"

#define BUF_SIZE 64
#define PAYLOAD "lwrb consumer payload 0123456789"

int
main(void) {
    lwrb_t buff;
    uint8_t storage[BUF_SIZE];
    uint8_t readback[BUF_SIZE];
    const char* payload = PAYLOAD;
    size_t payload_len = strlen(payload);
    size_t written, n_read, full;

    memset(&buff, 0, sizeof(buff));
    memset(readback, 0, sizeof(readback));

    if (!lwrb_init(&buff, storage, sizeof(storage))) {
        printf("FAIL: lwrb_init returned 0\n");
        return 1;
    }
    if (!lwrb_is_ready(&buff)) {
        printf("FAIL: lwrb_is_ready returned 0 after init\n");
        return 1;
    }

    written = lwrb_write(&buff, payload, payload_len);
    if (written != payload_len) {
        printf("FAIL: wrote %zu of %zu bytes\n", written, payload_len);
        return 1;
    }

    full = lwrb_get_full(&buff);
    if (full != payload_len) {
        printf("FAIL: lwrb_get_full = %zu, expected %zu\n", full, payload_len);
        return 1;
    }

    n_read = lwrb_read(&buff, readback, full);
    if (n_read != payload_len) {
        printf("FAIL: read %zu of %zu bytes\n", n_read, payload_len);
        return 1;
    }

    if (memcmp(readback, payload, payload_len) != 0) {
        printf("FAIL: read-back data mismatch\n");
        return 1;
    }

    if (lwrb_get_full(&buff) != 0) {
        printf("FAIL: buffer not empty after full read\n");
        return 1;
    }

    printf("PASS: lwrb consumer roundtrip OK (%zu bytes written/read,"
           " data verified)\n", written);
    return 0;
}