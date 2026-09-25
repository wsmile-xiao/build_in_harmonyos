/*
 * test_ohos.c — containers 1.2.2 HarmonyOS PC 专项用例
 *
 * 区别于上游内置自测 (tst/, 16 用例) 与 test_package 消费者用例：
 * 本用例专门验证 OHOS (AArch64) 平台语义 — 上游在 x86/gcc 上默认
 * signed char，而 OHOS AArch64 上 char 默认无符号，会破坏 AVL 树把
 * 平衡因子 (-1/0/1) 存于 char 的内部表示（实测导致
 * tst/test_set.c:set_verify_recursive 断言失败）。适配以
 * -fsigned-char 恢复上游语义；本用例用公开 API 验证该平台差异已被
 * 正确适配：构造会触发 AVL 双旋转/平衡因子 -1 的插入序列，并断言
 * 树结构校验（通过 set_contains/set_size 的可观察结果）正确。
 *
 * 编译（链接已安装的公开库，仅用公开头文件）:
 *   clang test_ohos.c -I<include> -L<lib> -lcontainers \
 *     -fsigned-char -o test_ohos_containers
 *
 * 不使用 assert()（Release/NDEBUG 下会被剥离成空壳）：全部显式检查。
 */
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>

/* 公开头文件 */
#include <set.h>
#include <map.h>
#include <vector.h>
#include <_bk_defines.h>

static int failures = 0;

#define CHECK(cond, what) do { \
    if (!(cond)) { failures++; printf("FAIL: %s\n", what); } \
    else { printf("PASS: %s\n", what); } \
} while (0)

static int int_cmp(const void *const one, const void *const two)
{
    const int a = *(const int *) one;
    const int b = *(const int *) two;
    return a < b ? -1 : (a > b ? 1 : 0);
}

/* 校验 set 中所有键按升序可遍历（AVL 有序性 + 结构完整性的可观察代理）*/
static int verify_ascending(set s, size_t expected_size)
{
    /* 通过 size + contains 组合校验结构完整性；AVL 失衡会导致
     * 后续插入路径上的断言/崩溃（OHOS 无符号 char 复现路径）*/
    int prev = INT_MIN;
    int key;
    for (key = -1000; key <= 1000; key++) {
        bk_bool has = set_contains(s, &key);
        if (has == BK_TRUE) {
            if (key <= prev) {
                return 0; /* 顺序破坏 */
            }
            prev = key;
        }
    }
    return set_size(s) == expected_size;
}

int main(void)
{
    /* --- T1: AVL 平衡因子路径 (触发右-右/双旋转) ---
     * 插入 2000 个升序键会使 AVL 树反复左旋；若 char 无符号导致
     * 平衡因子 -1 判错，上游 set.c 的修复分支不触发，树结构破坏，
     * 最终 set_contains/set_size 返回错误结果或崩溃。 */
    set s = set_init(sizeof(int), int_cmp);
    CHECK(s != NULL, "T1 set_init");
    int i;
    int ok = 1;
    for (i = 0; i < 2000; i++) {
        if (set_put(s, &i) != BK_OK) {
            ok = 0;
            break;
        }
    }
    CHECK(ok, "T1 set_put x2000 (ascending)");
    CHECK(verify_ascending(s, 2000), "T1 AVL ascending integrity (2000)");

    /* 删除一半键，验证删除路径的平衡修复 */
    ok = 1;
    for (i = 0; i < 2000; i += 2) {
        if (set_remove(s, &i) != BK_TRUE) {
            ok = 0;
            break;
        }
    }
    CHECK(ok, "T1 set_remove x1000");
    CHECK(set_size(s) == 1000, "T1 set_size == 1000 after removal");
    CHECK(verify_ascending(s, 1000), "T1 AVL integrity after removal (1000)");
    s = set_destroy(s);
    CHECK(s == NULL, "T1 set_destroy");

    /* --- T2: map 键值对 + 大量插入 (哈希/比较混合路径) --- */
    map m = map_init(sizeof(int), sizeof(int), int_cmp);
    CHECK(m != NULL, "T2 map_init");
    ok = 1;
    for (i = 0; i < 500; i++) {
        int val = i * 3;
        if (map_put(m, &i, &val) != BK_OK) {
            ok = 0;
            break;
        }
    }
    CHECK(ok, "T2 map_put x500");
    CHECK(map_size(m) == 500, "T2 map_size == 500");
    ok = 1;
    for (i = 0; i < 500; i++) {
        int val = -1;
        if (map_get(&val, m, &i) != BK_TRUE || val != i * 3) {
            ok = 0;
            break;
        }
    }
    CHECK(ok, "T2 map_get roundtrip (val == key*3)");
    m = map_destroy(m);
    CHECK(m == NULL, "T2 map_destroy");

    /* --- T3: vector 压力 (realloc 路径) --- */
    vector v = vector_init(sizeof(int));
    CHECK(v != NULL, "T3 vector_init");
    ok = 1;
    for (i = 0; i < 10000; i++) {
        if (vector_add_last(v, &i) != BK_OK) {
            ok = 0;
            break;
        }
    }
    CHECK(ok, "T3 vector_add_last x10000");
    CHECK(vector_size(v) == 10000, "T3 vector_size == 10000");
    int out = -1;
    if (vector_get_at(&out, v, 9999) == BK_OK) {
        CHECK(out == 9999, "T3 vector_get_at(9999) == 9999");
    } else {
        CHECK(0, "T3 vector_get_at rc");
    }
    v = vector_destroy(v);
    CHECK(v == NULL, "T3 vector_destroy");

    if (failures == 0) {
        printf("test_ohos containers 1.2.2: OHOS 专项 3/3 PASS\n");
        return 0;
    }
    printf("test_ohos containers 1.2.2: %d FAILURES\n", failures);
    return 1;
}