/*
 * test.c — mcmpq 消费者验证 (test_package L1)
 *
 * 模拟业务上层组件：仅通过 Conan 安装导出的公开头文件 mcmpq.h 与
 * 公开 API (enqueue/dequeue/try_enqueue/try_dequeue/HEAD/TAIL)
 * 编译、链接并正常运行，验证第三方使用者可用性。
 */
#include <stdio.h>
#include <string.h>
#include "mcmpq.h"

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void) {
    queue_t q;
    int item, out;

    /* 1. FIFO 全链路：enqueue 8 项 → dequeue 8 项，值一致且顺序保持 */
    memset(&q, 0, sizeof(q));
    for (int i = 0; i < 8; i++) {
        item = i * 10;
        enqueue(&q, &item);
    }
    for (int i = 0; i < 8; i++) {
        dequeue(&q, &out);
        CHECK(out == i * 10, "FIFO 顺序保持");
    }
    CHECK(HEAD(&q) - TAIL(&q) == 0, "队列已清空");

    /* 2. try 接口非阻塞语义 */
    memset(&q, 0, sizeof(q));
    CHECK(!try_dequeue(&q, &out), "空队列 try_dequeue=false");
    item = 42;
    CHECK(try_enqueue(&q, &item), "try_enqueue=true");
    CHECK(try_dequeue(&q, &out) && out == 42, "try_dequeue 取回 42");

    printf("mcmpq consumer test: %s\n", failures == 0 ? "ALL PASSED" : "FAILED");
    return failures == 0 ? 0 : 1;
}