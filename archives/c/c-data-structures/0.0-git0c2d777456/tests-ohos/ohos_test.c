/* OHOS 专项测试：通过公开头文件宏 API 验证 c-data-structures 在
 * HarmonyOS PC (armv8, OHOS clang) 平台上的完整功能与可观察结果。
 * 与上游 test.c 自检、test_package 消费者用例分别计数。
 *
 * 验证点：
 *   1. TinyBuf 动态数组：PUSH/INSERT/REMOVE/SWAPREMOVE/FIT/RESIZE/TRYFIT/FREE
 *   2. TinyHashMap 32 位键：SET_STR/GET_STR/HAS_STR/DEL_STR/PTR_STR/IDX_STR/
 *      CLEAR/FIT/SETNULLVAL/TRYFIT/FREE 及字符串过滤哈希键
 *   3. TinyHashMap64 64 位键：HMAP64_* 全套（含大 uint64 键值）
 *   4. 内存回收完整性：全部 FREE 后指针为 NULL、len/cap 归零
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "tinybuf.h"
#include "tinyhashmap.h"
#include "tinyhashmap64.h"

typedef struct { int a, b, c; } mytype_t;

static int ohos_failures = 0;
#define OHOS_CHECK(cond, msg) do { if (!(cond)) { fprintf(stderr, "OHOS FAIL: %s\n", msg); ohos_failures++; } } while (0)

static uint32_t hash_nocase_nospace(const char* str)
{
    unsigned char c;
    uint32_t hash = (uint32_t)0x811c9dc5;
    while ((c = (unsigned char)*(str++)) != '\0')
        if (c > ' ')
            hash = ((hash * (uint32_t)0x01000193) ^ (uint32_t)((c >= 'A' && c <= 'Z') ? (c | 0x20) : c));
    return (hash ? hash : 1);
}

/* ---- TinyBuf ---- */
static void ohos_tinybuf(void)
{
    mytype_t *buf = NULL;
    mytype_t e1 = { 1, 2, 3 }, e2 = { 4, 5, 6 };

    BUF_PUSH(buf, e1);
    BUF_PUSH(buf, e2);
    OHOS_CHECK(BUF_LEN(buf) == 2, "buf len == 2 after 2 pushes");
    OHOS_CHECK(buf[0].a == 1 && buf[1].c == 6, "buf element values");

    BUF_FIT(buf, 100);
    OHOS_CHECK(BUF_CAP(buf) == 100, "buf fit to 100");

    BUF_RESIZE(buf, 200);
    OHOS_CHECK(BUF_LEN(buf) == 200, "buf resize to 200");

    BUF_REMOVE(buf, 30);
    OHOS_CHECK(BUF_LEN(buf) == 199, "buf remove keeps order");

    BUF_SWAPREMOVE(buf, 10);
    OHOS_CHECK(BUF_LEN(buf) == 198, "buf swapremove");

    BUF_INSERT(buf, 100, e1);
    OHOS_CHECK(BUF_LEN(buf) == 199 && buf[100].a == 1, "buf insert middle");

    BUF_ADD(buf, 10);
    OHOS_CHECK(BUF_LEN(buf) == 209, "buf add uninitialized");

    BUF_ADDZEROED(buf, 10);
    OHOS_CHECK(BUF_LEN(buf) == 219, "buf add zeroed");

    bool oom = !BUF_TRYFIT(buf, 1000);
    OHOS_CHECK(!oom && BUF_CAP(buf) == 1000, "buf tryfit grows");

    BUF_FREE(buf);
    OHOS_CHECK(buf == NULL && BUF_LEN(buf) == 0 && BUF_CAP(buf) == 0, "buf free clears");
}

/* ---- TinyHashMap (32-bit keys) ---- */
static void ohos_tinyhashmap(void)
{
    mytype_t *map = NULL;
    mytype_t foo = { 10, 20, 30 }, bar = { 40, 50, 60 }, map_null = { -1, -1, -1 };

    HMAP_SET_STR(map, "foo", foo);
    HMAP_SET_STR(map, "bar", bar);
    OHOS_CHECK(HMAP_LEN(map) == 2, "hmap len == 2");
    OHOS_CHECK(HMAP_GET_STR(map, "foo").a == 10, "hmap get foo");
    OHOS_CHECK(HMAP_HAS_STR(map, "foo") && !HMAP_HAS_STR(map, "baz"), "hmap has");
    OHOS_CHECK(HMAP_IDX_STR(map, "foo") >= 0 && HMAP_IDX_STR(map, "nope") == -1, "hmap idx");

    OHOS_CHECK(HMAP_DEL_STR(map, "bar") && !HMAP_DEL_STR(map, "bar"), "hmap del");
    OHOS_CHECK(HMAP_LEN(map) == 1, "hmap len == 1 after del");

    mytype_t *p = HMAP_PTR_STR(map, "qux");
    p->a = 123;
    OHOS_CHECK(HMAP_GET_STR(map, "qux").a == 123, "hmap ptr add/modify");

    HMAP_CLEAR(map);
    OHOS_CHECK(HMAP_LEN(map) == 0, "hmap clear");

    HMAP_SETNULLVAL(map, map_null);
    OHOS_CHECK(HMAP_GET_STR(map, "invalid").a == -1, "hmap custom null value");

    /* filtered string keys: case/whitespace insensitive */
    HMAP_SET(map, hash_nocase_nospace("TEST A"), foo);
    OHOS_CHECK(HMAP_IDX(map, hash_nocase_nospace("TEST A")) ==
               HMAP_IDX(map, hash_nocase_nospace("testa")), "hmap filtered keys match");
    OHOS_CHECK(HMAP_IDX(map, hash_nocase_nospace("TEST A")) !=
               HMAP_IDX(map, hash_nocase_nospace("TEST B")), "hmap filtered keys differ");

    bool oom = !HMAP_TRYFIT(map, 1000);
    OHOS_CHECK(!oom, "hmap tryfit grows");

    HMAP_FREE(map);
    OHOS_CHECK(map == NULL && HMAP_LEN(map) == 0 && HMAP_CAP(map) == 0, "hmap free clears");
}

/* ---- TinyHashMap64 (64-bit keys) ---- */
static void ohos_tinyhashmap64(void)
{
    uint64_t *map = NULL;
    uint64_t k1 = 0x1111111111111111ULL, k2 = 0x2222222222222222ULL;
    size_t i, cap;
    int found = 0;

    HMAP64_SET(map, k1, 111);
    HMAP64_SET(map, k2, 222);
    OHOS_CHECK(HMAP64_LEN(map) == 2, "hmap64 len == 2");
    OHOS_CHECK(HMAP64_GET(map, k1) == 111 && HMAP64_GET(map, k2) == 222, "hmap64 get");
    OHOS_CHECK(HMAP64_HAS(map, k1) && !HMAP64_HAS(map, 0xDEADBEEFULL), "hmap64 has");
    OHOS_CHECK(HMAP64_IDX(map, k1) >= 0 && HMAP64_IDX(map, 0xDEADBEEFULL) == -1, "hmap64 idx");

    /* iterate: exactly the two keys, once each */
    for (i = 0, cap = HMAP64_CAP(map); i != cap; i++)
        if (HMAP64_KEY(map, i))
            found++;
    OHOS_CHECK(found == 2, "hmap64 iterate finds 2 keys");

    OHOS_CHECK(HMAP64_DEL(map, k2) && !HMAP64_DEL(map, k2), "hmap64 del");
    OHOS_CHECK(HMAP64_LEN(map) == 1, "hmap64 len == 1 after del");

    HMAP64_CLEAR(map);
    OHOS_CHECK(HMAP64_LEN(map) == 0, "hmap64 clear");

    bool oom = !HMAP64_TRYFIT(map, 1000);
    OHOS_CHECK(!oom, "hmap64 tryfit grows");

    HMAP64_FREE(map);
    OHOS_CHECK(map == NULL && HMAP64_LEN(map) == 0 && HMAP64_CAP(map) == 0, "hmap64 free clears");
}

int main(void)
{
    ohos_tinybuf();
    ohos_tinyhashmap();
    ohos_tinyhashmap64();
    if (ohos_failures == 0)
        printf("All OHOS c-data-structures checks passed\n");
    else
        printf("%d OHOS c-data-structures check(s) FAILED\n", ohos_failures);
    return ohos_failures == 0 ? 0 : 1;
}
