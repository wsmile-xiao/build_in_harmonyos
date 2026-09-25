/*
 * test_package consumer test — containers 1.2.2 on OHOS.
 *
 * Consumes ONLY the installed public headers + library (containers::containers):
 * exercises vector (dynamic array), set (AVL tree) and stack public APIs exactly
 * as a third-party application would, and checks observable results.
 *
 * NOTE: must not rely on assert() — CMake Release builds define -DNDEBUG which
 * strips assert entirely (would make this an empty-shell test, R34/PF3).
 * All checks are explicit if/return with a printed result.
 */
#include <stdio.h>
#include <string.h>

/* Public headers shipped in the package include/ dir */
#include <vector.h>
#include <set.h>
#include <stack.h>
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

int main(void)
{
    /* --- vector: add_last / get_at / size / clear --- */
    vector v = vector_init(sizeof(int));
    CHECK(v != NULL, "vector_init");
    int data[5] = {10, 20, 30, 40, 50};
    int i;
    for (i = 0; i < 5; i++) {
        CHECK(vector_add_last(v, &data[i]) == BK_OK, "vector_add_last");
    }
    CHECK(vector_size(v) == 5, "vector_size == 5");
    for (i = 0; i < 5; i++) {
        int out = -1;
        if (vector_get_at(&out, v, (size_t) i) == BK_OK) {
            CHECK(out == data[i], "vector_get_at value");
        } else {
            CHECK(0, "vector_get_at rc");
        }
    }
    v = vector_destroy(v);
    CHECK(v == NULL, "vector_destroy");

    /* --- set: unique keys, sorted order, contains --- */
    set s = set_init(sizeof(int), int_cmp);
    CHECK(s != NULL, "set_init");
    int keys[5] = {42, 7, 99, 7, 1}; /* duplicate 7 must collapse */
    for (i = 0; i < 5; i++) {
        CHECK(set_put(s, &keys[i]) == BK_OK, "set_put");
    }
    CHECK(set_size(s) == 4, "set_size == 4 (dup collapsed)");
    int probe = 42;
    CHECK(set_contains(s, &probe) == BK_TRUE, "set_contains 42");
    probe = 7;
    CHECK(set_contains(s, &probe) == BK_TRUE, "set_contains 7");
    probe = 999;
    CHECK(set_contains(s, &probe) == BK_FALSE, "set_contains 999 absent");
    probe = 7;
    CHECK(set_remove(s, &probe) == BK_TRUE, "set_remove 7");
    CHECK(set_size(s) == 3, "set_size == 3 after remove");
    s = set_destroy(s);
    CHECK(s == NULL, "set_destroy");

    /* --- stack: LIFO order --- */
    stack st = stack_init(sizeof(int));
    CHECK(st != NULL, "stack_init");
    for (i = 0; i < 4; i++) {
        CHECK(stack_push(st, &data[i]) == BK_OK, "stack_push");
    }
    int out = -1;
    if (stack_pop(&out, st) == BK_TRUE) {
        CHECK(out == 40, "stack LIFO pop == 40");
    } else {
        CHECK(0, "stack_pop rc");
    }
    st = stack_destroy(st);
    CHECK(st == NULL, "stack_destroy");

    if (failures == 0) {
        printf("test containers 1.2.2: consumer OK (vector/set/stack verified)\n");
        return 0;
    }
    printf("test containers 1.2.2: %d FAILURES\n", failures);
    return 1;
}