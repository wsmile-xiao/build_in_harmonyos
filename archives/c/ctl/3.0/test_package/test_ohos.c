/*
 * ctl 3.0 HarmonyOS 专项测试（OS-toolchain 真实运行，独立于上游 func 用例）。
 *
 * 目的：在 OHOS（aarch64-unknown-linux-ohos-clang 15，libc++17）交叉工具链下，
 * 验证 ctl 公开头文件（vec/lst/deq/set/ust/stk/que/pqu）实例化后的真实内存
 * 生命周期：init → push/insert → iterate/sort → erase → free，断言覆盖
 * 公开 API 的可观察结果。注意：每个容器头文件末尾会 #undef T，因此每个
 * 头文件必须在其 include 前单独定义 P/T（与上游 tests/func 用法一致）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define P
#define T int
#include <vec.h>

#define P
#define T int
#include <lst.h>

#define P
#define T int
#include <deq.h>

#define P
#define T int
#include <stk.h>

#define P
#define T int
#include <que.h>

#define P
#define T int
#include <pqu.h>

#define P
#define T int
#include <set.h>

#define P
#define T int
#include <ust.h>

static int
int_less(int* a, int* b)
{
    /* vec sort 语义：compare(a,i) 为真时交换 → 返回 a>b 得到升序结果
     * （与上游 test_str.cc char_compare 语义一致） */
    return *a > *b;
}

static int
int_greater(int* a, int* b)
{
    return *a > *b;
}

static int
int_compare3(int* a, int* b)
{
    /* set 需要三态比较器：0 相等 / <0 a小 / >0 a大（同上游 digi_key_compare） */
    return (*a > *b) - (*a < *b);
}

static int
int_equal(int* a, int* b)
{
    return *a == *b;
}

static size_t
int_hash(int* x)
{
    return (size_t) abs(*x);
}

int
main(void)
{
    int rc = 0;

    /* vec: push_back + sort + iterate 的可观察结果 */
    vec_int v = vec_int_init();
    vec_int_push_back(&v, 5);
    vec_int_push_back(&v, 1);
    vec_int_push_back(&v, 4);
    vec_int_push_back(&v, 2);
    vec_int_push_back(&v, 3);
    vec_int_sort(&v, int_less);
    int expected_vec[5] = {1, 2, 3, 4, 5};
    if (v.size != 5)
        rc = 1;
    for (size_t i = 0; i < 5 && rc == 0; i++)
        if (*vec_int_at(&v, i) != expected_vec[i])
            rc = 2;
    vec_int_free(&v);

    /* lst: 双向链表 push/erase（insert 需要 node 位置，取迭代器 .node） */
    lst_int l = lst_int_init();
    lst_int_push_back(&l, 10);
    lst_int_push_back(&l, 30);
    lst_int_it lit = lst_int_it_each(&l);
    lit.step(&lit); /* 移到 30 所在节点 */
    lst_int_insert(&l, lit.node, 20);
    if (rc == 0 && l.size != 3)
        rc = 3;
    lst_int_erase(&l, lit.node);
    if (rc == 0 && l.size != 2)
        rc = 4;
    lst_int_free(&l);

    /* deq: 双端 push_front/push_back */
    deq_int d = deq_int_init();
    deq_int_push_back(&d, 1);
    deq_int_push_front(&d, 0);
    deq_int_push_back(&d, 2);
    if (rc == 0 && (d.size != 3 || *deq_int_at(&d, 0) != 0 || *deq_int_at(&d, 2) != 2))
        rc = 5;
    deq_int_free(&d);

    /* set: 排序集合去重 + find/count（三态比较器） */
    set_int s = set_int_init(int_compare3);
    set_int_insert(&s, 3);
    set_int_insert(&s, 1);
    set_int_insert(&s, 3);
    set_int_insert(&s, 2);
    if (rc == 0 && (s.size != 3 || set_int_count(&s, 2) != 1))
        rc = 6;
    set_int_erase(&s, 1);
    if (rc == 0 && s.size != 2)
        rc = 7;
    set_int_free(&s);

    /* ust: 无序集合哈希查找 */
    ust_int u = ust_int_init(int_hash, int_equal);
    ust_int_insert(&u, 42);
    ust_int_insert(&u, 7);
    if (rc == 0 && (u.size != 2 || ust_int_find(&u, 42) == NULL))
        rc = 8;
    ust_int_free(&u);

    /* stk: 栈 */
    stk_int st = stk_int_init();
    stk_int_push(&st, 1);
    stk_int_push(&st, 2);
    if (rc == 0 && (*stk_int_top(&st) != 2 || st.size != 2))
        rc = 9;
    stk_int_pop(&st);
    if (rc == 0 && *stk_int_top(&st) != 1)
        rc = 10;
    stk_int_free(&st);

    /* que: 队列 */
    que_int q = que_int_init();
    que_int_push(&q, 1);
    que_int_push(&q, 2);
    if (rc == 0 && (*que_int_front(&q) != 1 || *que_int_back(&q) != 2 || q.size != 2))
        rc = 11;
    que_int_pop(&q);
    if (rc == 0 && *que_int_front(&q) != 2)
        rc = 12;
    que_int_free(&q);

    /* pqu: 优先队列（compare 语义同上游 digi_compare：*b < *a 时 swap → 大顶堆） */
    pqu_int pq = pqu_int_init(int_greater);
    pqu_int_push(&pq, 3);
    pqu_int_push(&pq, 1);
    pqu_int_push(&pq, 2);
    if (rc == 0 && *pqu_int_top(&pq) != 3)
        rc = 13;
    pqu_int_pop(&pq);
    if (rc == 0 && *pqu_int_top(&pq) != 2)
        rc = 14;
    pqu_int_free(&pq);

    if (rc == 0)
        printf("ctl 3.0 OHOS 专项测试: PASS (vec/lst/deq/set/ust/stk/que/pqu 全通过)\n");
    else
        printf("ctl 3.0 OHOS 专项测试: FAIL (rc=%d)\n", rc);
    return rc;
}