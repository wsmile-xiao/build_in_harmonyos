#include <c-list.h>

#include <assert.h>
#include <stdio.h>

int main(void) {
    CList list = C_LIST_INIT(list);
    CList a, b, c;
    CList *iter;
    unsigned int n;

    /* 1) 空链表两端不可见 */
    assert(!c_list_first(&list));
    assert(!c_list_last(&list));

    /* 2) 未链接节点不可见，链接后可见 */
    assert(!c_list_is_linked(&a));
    c_list_link_tail(&list, &a);
    c_list_link_tail(&list, &b);
    c_list_link_tail(&list, &c);
    assert(c_list_is_linked(&a));

    /* 3) 尾插顺序正确 */
    assert(c_list_first(&list) == &a);
    assert(c_list_last(&list) == &c);

    /* 4) 正向遍历计数 */
    n = 0;
    c_list_for_each(iter, &list)
            ++n;
    assert(n == 3);

    /* 5) 摘除中间节点后遍历计数 */
    c_list_unlink(&b);
    assert(!c_list_is_linked(&b));
    n = 0;
    c_list_for_each(iter, &list)
            ++n;
    assert(n == 2);

    /* 6) 摘除头节点后首元素更新 */
    c_list_unlink(&a);
    assert(c_list_first(&list) == &c);

    /* 7) 清空后回到空表状态 */
    c_list_unlink(&c);
    assert(!c_list_is_linked(&c));
    assert(!c_list_first(&list));

    printf("c-list consumer test PASSED: link/iterate/unlink/empty checks passed\n");
    return 0;
}
