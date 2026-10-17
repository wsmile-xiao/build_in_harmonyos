/*
 * ohos_specific.c - HarmonyOS PC (aarch64-linux-ohos) 专项测试
 *
 * 验证 mcmpq.h 公开 API 在 OHOS 工具链下的可用性与语义：
 *  - try_enqueue/try_dequeue 非阻塞语义（空队列返回 false，满队列返回 false）
 *  - enqueue/dequeue 阻塞语义（单生产者单消费者全链路 FIFO）
 *  - 队列容量 SLOTS 边界行为（满队列后 try_enqueue 必须返回 false）
 *  - 数据完整性（出入队值一致）
 */
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include "mcmpq.h"

static int tests_run = 0;
static int tests_passed = 0;

#define CHECK(cond, msg) do { \
    tests_run++; \
    if (cond) { tests_passed++; printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s (line %d)\n", msg, __LINE__); } \
} while (0)

int main(void) {
    queue_t q;
    int item, out;

    /* 1. 空队列 try_dequeue 必须返回 false */
    memset(&q, 0, sizeof(q));
    CHECK(!try_dequeue(&q, &out), "空队列 try_dequeue 返回 false");

    /* 2. 单元素 FIFO：enqueue 后 dequeue 值一致 */
    memset(&q, 0, sizeof(q));
    item = 42;
    enqueue(&q, &item);
    dequeue(&q, &out);
    CHECK(out == 42, "单元素 FIFO 值一致 (42)");

    /* 3. 多元素 FIFO 顺序保持 */
    memset(&q, 0, sizeof(q));
    for (int i = 0; i < SLOTS; i++) {
        item = i * 100;
        enqueue(&q, &item);
    }
    for (int i = 0; i < SLOTS; i++) {
        dequeue(&q, &out);
        CHECK(out == i * 100, "FIFO 顺序保持");
    }

    /* 4. 队列填满 SLOTS 后 try_enqueue 必须返回 false */
    memset(&q, 0, sizeof(q));
    for (int i = 0; i < SLOTS; i++) {
        item = i;
        enqueue(&q, &item);
    }
    CHECK(HEAD(&q) - TAIL(&q) == SLOTS, "队列已填满 SLOTS 项");
    item = 999;
    CHECK(!try_enqueue(&q, &item), "满队列 try_enqueue 返回 false");

    /* 5. try_enqueue 成功后 try_dequeue 可取回 */
    memset(&q, 0, sizeof(q));
    item = 7;
    CHECK(try_enqueue(&q, &item), "try_enqueue 成功");
    CHECK(try_dequeue(&q, &out), "try_dequeue 成功");
    CHECK(out == 7, "try 路径值一致 (7)");

    /* 6. HEAD/TAIL 宏：空队列时相等 */
    memset(&q, 0, sizeof(q));
    CHECK(HEAD(&q) == TAIL(&q), "空队列 HEAD == TAIL");

    printf("\nOHOS 专项测试结果: %d/%d 通过\n", tests_passed, tests_run);
    return tests_passed == tests_run ? 0 : 1;
}
