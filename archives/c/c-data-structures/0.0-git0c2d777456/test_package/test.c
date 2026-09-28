#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

/* Real consumer test: exercise the public header-only API end-to-end.
 * Only the installed public headers are used (R34) — a business-like
 * consumer linking against the library's exported interfaces. */

#include "tinybuf.h"
#include "tinyhashmap.h"
#include "tinyhashmap64.h"

typedef struct { int a, b, c; } mytype_t;

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } } while (0)

static void test_tinybuf(void)
{
    mytype_t* buf = NULL;
    mytype_t e1 = {1, 2, 3};
    mytype_t e2 = {4, 5, 6};
    BUF_PUSH(buf, e1);
    BUF_PUSH(buf, e2);
    CHECK(BUF_LEN(buf) == 2, "BUF_LEN == 2 after two pushes");
    CHECK(buf[0].a == 1 && buf[0].b == 2 && buf[0].c == 3, "buf[0] == e1");
    CHECK(buf[1].a == 4 && buf[1].b == 5 && buf[1].c == 6, "buf[1] == e2");

    /* insert into the middle */
    mytype_t e3 = {7, 8, 9};
    BUF_INSERT(buf, 1, e3);
    CHECK(BUF_LEN(buf) == 3, "BUF_LEN == 3 after insert");
    CHECK(buf[1].a == 7, "inserted element at index 1");

    /* remove keeping order */
    BUF_REMOVE(buf, 1);
    CHECK(BUF_LEN(buf) == 2, "BUF_LEN == 2 after remove");
    CHECK(buf[1].a == 4, "order preserved after remove");

    /* swap-remove */
    BUF_SWAPREMOVE(buf, 0);
    CHECK(BUF_LEN(buf) == 1, "BUF_LEN == 1 after swapremove");

    BUF_FREE(buf);
    CHECK(buf == NULL && BUF_LEN(buf) == 0 && BUF_CAP(buf) == 0, "BUF_FREE clears buf");
}

static void test_tinyhashmap(void)
{
    mytype_t* map = NULL;
    mytype_t foo = {10, 20, 30};
    mytype_t bar = {40, 50, 60};

    HMAP_SET_STR(map, "foo", foo);
    HMAP_SET_STR(map, "bar", bar);
    CHECK(HMAP_LEN(map) == 2, "HMAP_LEN == 2");
    CHECK(HMAP_GET_STR(map, "foo").a == 10, "HMAP_GET_STR foo");
    CHECK(HMAP_GET_STR(map, "bar").c == 60, "HMAP_GET_STR bar");
    CHECK(HMAP_HAS_STR(map, "foo"), "HMAP_HAS_STR foo present");
    CHECK(!HMAP_HAS_STR(map, "baz"), "HMAP_HAS_STR baz absent");
    CHECK(HMAP_IDX_STR(map, "foo") >= 0, "HMAP_IDX_STR foo >= 0");
    CHECK(HMAP_IDX_STR(map, "invalid") == -1, "HMAP_IDX_STR invalid == -1");

    CHECK(HMAP_DEL_STR(map, "bar"), "HMAP_DEL_STR bar removed");
    CHECK(!HMAP_DEL_STR(map, "bar"), "second remove returns false");
    CHECK(HMAP_LEN(map) == 1, "HMAP_LEN == 1 after delete");

    mytype_t* p = HMAP_PTR_STR(map, "qux");
    p->a = 123;
    CHECK(HMAP_GET_STR(map, "qux").a == 123, "HMAP_PTR_STR add/modify via pointer");

    HMAP_FREE(map);
    CHECK(map == NULL && HMAP_LEN(map) == 0, "HMAP_FREE clears map");
}

static void test_tinyhashmap64(void)
{
    uint64_t* map = NULL;
    HMAP64_SET(map, 0x100000000ULL, 11);
    HMAP64_SET(map, 0x200000000ULL, 22);
    CHECK(HMAP64_LEN(map) == 2, "HMAP64_LEN == 2");
    CHECK(HMAP64_GET(map, 0x100000000ULL) == 11, "HMAP64_GET key1");
    CHECK(HMAP64_GET(map, 0x200000000ULL) == 22, "HMAP64_GET key2");
    CHECK(!HMAP64_HAS(map, 0xDEADBEEFULL), "HMAP64_HAS unknown key");
    HMAP64_FREE(map);
    CHECK(map == NULL, "HMAP64_FREE clears map");
}

int main(void)
{
    test_tinybuf();
    test_tinyhashmap();
    test_tinyhashmap64();
    if (failures == 0)
        printf("All c-data-structures consumer checks passed\n");
    else
        printf("%d c-data-structures consumer check(s) FAILED\n", failures);
    return failures == 0 ? 0 : 1;
}
