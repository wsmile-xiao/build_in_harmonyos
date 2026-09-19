#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "clibs/list.h"

/* 消费者用例（消费者可用性硬门禁）：
 * 模拟业务上层组件，仅通过库已安装/导出的公开头文件 <clibs/list.h>
 * 与公开 API（list_new/list_rpush/list_lpush/list_find/list_at/
 * list_rpop/list_lpop/list_remove/list_destroy/list_iterator_*）
 * 编译、链接并调用，验证第三方使用者可正常使用本库。
 *
 * 业务场景：任务调度队列 —— rpush 入队、lpop 出队、find 按标识检索、
 * at 随机访问、迭代器遍历输出，全部通过公开 API 完成。 */
int main(void) {
    list_t *queue = list_new();
    assert(queue != NULL);

    /* 入队 3 个任务标识 */
    const char *tasks[] = {"build-core", "run-tests", "publish-artifact"};
    for (int i = 0; i < 3; i++) {
        list_node_t *n = list_node_new((char *)tasks[i]);
        assert(n != NULL);
        list_rpush(queue, n);
    }
    assert(queue->len == 3);

    /* 按标识检索 */
    list_node_t *hit = list_find(queue, "run-tests");
    assert(hit != NULL);
    assert(0 == strcmp((char *)hit->val, "run-tests"));
    assert(NULL == list_find(queue, "no-such-task"));

    /* 随机访问 */
    assert(0 == strcmp((char *)list_at(queue, 0)->val, "build-core"));
    assert(0 == strcmp((char *)list_at(queue, -1)->val, "publish-artifact"));

    /* 迭代器遍历（正向），验证完整顺序 */
    int idx = 0;
    list_iterator_t *it = list_iterator_new(queue, LIST_HEAD);
    list_node_t *cur;
    while ((cur = list_iterator_next(it)) != NULL) {
        assert(0 == strcmp((char *)cur->val, tasks[idx++]));
    }
    assert(idx == 3);
    list_iterator_destroy(it);

    /* FIFO 出队 */
    list_node_t *first = list_lpop(queue);
    assert(first != NULL);
    assert(0 == strcmp((char *)first->val, "build-core"));
    free(first);
    assert(queue->len == 2);

    /* 移除中间节点 */
    list_remove(queue, queue->tail);
    assert(queue->len == 1);

    list_destroy(queue);
    printf("list 0.4.1 consumer test (public API via clibs/list.h): OK\n");
    return 0;
}