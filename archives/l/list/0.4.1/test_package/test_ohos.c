#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "clibs/list.h"

/* HarmonyOS / aarch64 专项测试（消费者视角）：
 * 通过已安装的公开头文件与静态库验证 OHOS 平台行为：
 * 1) 大容量节点压力（100 万节点 rpush + destroy），验证 OHOS 默认
 *    分配器下 malloc/free 与 list_destroy 递归释放的稳定性；
 * 2) 负索引与越界语义（list_at 负索引从尾部取、越界返回 NULL）；
 * 3) 双向迭代器遍历。 */
int main(void) {
    /* 1) 大容量压力 */
    list_t *list = list_new();
    assert(list != NULL);
    const int N = 1000000;
    for (int i = 0; i < N; i++) {
        list_node_t *node = list_node_new(NULL);
        assert(node != NULL);
        list_rpush(list, node);
    }
    assert(list->len == (unsigned int)N);
    assert(list_at(list, N - 1) != NULL);
    assert(NULL == list_at(list, N));
    list_destroy(list);

    /* 2) 负索引/越界 */
    list = list_new();
    const char *vals[] = {"a", "b", "c"};
    for (int i = 0; i < 3; i++) list_rpush(list, list_node_new((char *)vals[i]));
    assert(0 == strcmp((char *)list_at(list, -1)->val, "c"));
    assert(0 == strcmp((char *)list_at(list, -3)->val, "a"));
    assert(NULL == list_at(list, -4));

    /* 3) 双向迭代器 */
    int idx = 2;
    list_iterator_t *it = list_iterator_new(list, LIST_TAIL);
    list_node_t *cur;
    while ((cur = list_iterator_next(it)) != NULL)
        assert(0 == strcmp((char *)cur->val, vals[idx--]));
    assert(idx == -1);
    list_iterator_destroy(it);

    list_destroy(list);
    printf("list 0.4.1 HarmonyOS 专项测试 (aarch64-ohos): OK\n");
    return 0;
}