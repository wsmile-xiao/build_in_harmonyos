/*
 * test_package/test_kysdk.c —— libkysdk-base 消费者测试（Conan L1 / R34）
 *
 * 链接被测包安装后的共享库，调用两个模块的公开 API：
 *   1) kydatastruct（跳表）：插入 / 查找 / 删除，验证数据一致性与删除语义
 *   2) kyutils（容量进制转换）：1024KB -> 1MB
 *
 * 断言失败计数 > 0 时返回 1，使 conan create 的 test() 失败。
 * 键值查找语义（与上游一致）：查不到时 kysdk_skiplist_search().num == -1。
 */
#include <stdio.h>
#include <stdlib.h>

#include <skip_linklist.h>
#include <kyutils.h>

#define KEY_COUNT 64

static int failures = 0;

#define CHECK(cond, msg)                                                      \
    do {                                                                      \
        if (cond) {                                                           \
            printf("PASS: %s\n", (msg));                                      \
        } else {                                                              \
            printf("FAIL: %s\n", (msg));                                      \
            failures++;                                                       \
        }                                                                     \
    } while (0)

static void test_skiplist(void)
{
    kysdk_skiplist *list = kysdk_create_skiplist();
    int i, ok;

    CHECK(list != NULL, "kysdk_create_skiplist() 返回非空");
    if (list == NULL) {
        return;
    }

    ok = (kysdk_skiplist_setmaxlevels(list, 5) == 0);
    CHECK(ok, "kysdk_skiplist_setmaxlevels(5) 返回 0");

    ok = 1;
    for (i = 0; i < KEY_COUNT; i++) {
        kysdk_listdata d;
        d.num = i * 3 + 1;
        if (kysdk_skiplist_insert(list, i, d) != 0) {
            ok = 0;
        }
    }
    CHECK(ok, "kysdk_skiplist_insert() 连续插入 64 个键均返回 0");

    ok = 1;
    for (i = 0; i < KEY_COUNT; i++) {
        kysdk_listdata r = kysdk_skiplist_search(list, i);
        if (r.num != i * 3 + 1) {
            ok = 0;
            printf("  key=%d 期望 %d，实际 %d\n", i, i * 3 + 1, r.num);
        }
    }
    CHECK(ok, "kysdk_skiplist_search() 64 个键全部命中且数据一致");

    ok = (kysdk_skiplist_delete(list, 7) == 0);
    CHECK(ok, "kysdk_skiplist_delete(key=7) 返回 0");
    CHECK(kysdk_skiplist_search(list, 7).num == -1,
          "删除后 kysdk_skiplist_search(key=7) 返回 -1（未找到）");
    CHECK(kysdk_skiplist_search(list, 8).num == 25,
          "相邻键 key=8 未受影响（值 25）");

    kysdk_destroy_skiplist(list);
    printf("PASS: kysdk_destroy_skiplist() 正常返回\n");
}

static void test_kyutils(void)
{
    double out = -1.0;
    int rc = kdkVolumeBaseNumericalConvert(1024.0, KDK_KILOBYTE,
                                           KDK_MEGABYTE, &out);

    CHECK(rc == KDK_NOERR, "kdkVolumeBaseNumericalConvert() 返回 KDK_NOERR");
    CHECK(out > 0.99 && out < 1.01, "1024KB -> 1MB（容差 1%）");
}

int main(void)
{
    printf("== libkysdk-base consumer test ==\n");
    test_skiplist();
    test_kyutils();
    printf("total failures = %d\n", failures);
    return failures == 0 ? 0 : 1;
}
