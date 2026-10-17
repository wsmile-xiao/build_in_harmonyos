/*
 * test_blocks_c.c — independent C consumer of the installed BlocksRuntime.
 *
 * This is NOT the upstream test (that one is test_upstream.c). It is a second
 * consumer that exercises the same runtime from a different angle: stack vs
 * heap vs global block classes, the retain/release lifecycle, __block (byref)
 * assign/dispose, blocks crossing function boundaries and blocks as arguments.
 * Every check is a real runtime observation, not a compile-only probe.
 */
#include <stdio.h>
#include <string.h>

#include <Block.h>
#include <Block_private.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        checks++;                                                              \
        if (!(cond)) {                                                         \
            failures++;                                                        \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);             \
        }                                                                      \
    } while (0)

static int (^make_counter(int start))(void)
{
    __block int i = start;
    int (^b)(void) = ^{ return ++i; };
    return Block_copy(b);
}

static int apply(int (^f)(int), int v)
{
    return f(v);
}

int main(void)
{
    /* 1. capture by value */
    int a = 41;
    int (^b1)(int) = ^(int x) { return x + a; };
    CHECK(b1(1) == 42);

    /* 2. stack block lives in _NSConcreteStackBlock */
    CHECK(((struct Block_layout *)b1)->isa == (void *)_NSConcreteStackBlock);

    /* 3. __block mutation on a stack block */
    __block int counter = 0;
    void (^inc)(void) = ^{ counter++; };
    inc();
    inc();
    inc();
    CHECK(counter == 3);

    /* 4. Block_copy makes a heap copy of a stack block.
     * Note: this runtime (0.4.1) does not retag isa to _NSConcreteMallocBlock;
     * the heap copy is identified by BLOCK_NEEDS_FREE + refcount 1, and it is
     * a distinct allocation from the stack block. */
    int (^b2)(int) = Block_copy(b1);
    CHECK(b2(1) == 42);
    CHECK((const void *)b2 != (const void *)b1);
    CHECK(((struct Block_layout *)b2)->flags & BLOCK_NEEDS_FREE);
    CHECK((((struct Block_layout *)b2)->flags & BLOCK_REFCOUNT_MASK) == 1);
    Block_release(b2);

    /* 5. no-capture block is a global block */
    int (^gb)(int) = ^(int x) { return x + 7; };
    CHECK(((struct Block_layout *)gb)->isa == (void *)_NSConcreteGlobalBlock);
    CHECK(gb(35) == 42);

    /* 6. heap block outlives its defining scope; byref assign/dispose run */
    int (^counter_fn)(void) = make_counter(10);
    CHECK(counter_fn() == 11);
    CHECK(counter_fn() == 12);
    Block_release(counter_fn);

    /* 7. __block variable is shared through the byref forwarding pointer, and
     * the compiler emits copy/dispose helpers (BLOCK_HAS_COPY_DISPOSE) that
     * call _Block_object_assign / _Block_object_dispose for the byref. */
    __block int shared = 5;
    int (^read_shared)(void) = Block_copy(^{ return shared; });
    CHECK(((struct Block_layout *)read_shared)->flags & BLOCK_HAS_COPY_DISPOSE);
    shared = 6;
    CHECK(read_shared() == 6);
    Block_release(read_shared);

    /* 8. block as a function argument */
    CHECK(apply(^(int v) { return v * 2; }, 21) == 42);

    /* 9. nested block */
    int (^outer)(int) = ^(int x) { return (^{ return x + 1; })(); };
    CHECK(outer(41) == 42);

    /* 10. array of heap blocks (capture non-const locals so they are stack
     * blocks, not global blocks) */
    int v0 = 10, v1 = 11, v2 = 12;
    int (^arr[3])(void);
    arr[0] = Block_copy(^{ return v0; });
    arr[1] = Block_copy(^{ return v1; });
    arr[2] = Block_copy(^{ return v2; });
    CHECK(arr[0]() == 10 && arr[1]() == 11 && arr[2]() == 12);
    for (int i = 0; i < 3; i++) {
        CHECK(((struct Block_layout *)arr[i])->flags & BLOCK_NEEDS_FREE);
        Block_release(arr[i]);
    }

    /* 11. struct captured by value */
    struct pair { int x; int y; } p = {40, 2};
    int (^sum)(void) = ^{ return p.x + p.y; };
    CHECK(sum() == 42);

    /* 12. NULL handling (0.4.1 explicitly guards both entry points) */
    CHECK(Block_copy(NULL) == NULL);
    Block_release(NULL);

    /* Note: the runtime's _Block_dump() diagnostic is intentionally not called.
     * It exits(1) for blocks compiled by modern clang, because clang no longer
     * sets the legacy BLOCK_HAS_DESCRIPTOR bit that _Block_dump() insists on. */

    printf("test_blocks_c: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
