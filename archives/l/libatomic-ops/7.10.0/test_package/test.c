#include <stdio.h>

#include "atomic_ops.h"
#include "atomic_ops_malloc.h"
#include "atomic_ops_stack.h"

/* Always-active check: unlike assert(), it is NOT compiled out under
   NDEBUG/Release, so the consumer test stays a real functional check
   rather than degrading to a link-only check. */
#define CHECK(cond)                                    \
    do {                                               \
        if (!(cond)) {                                 \
            fprintf(stderr, "CHECK FAILED: %s (line %d)\n", \
                    #cond, __LINE__);                  \
            return 1;                                  \
        }                                              \
    } while (0)

int main(void) {
    /* 1. AO_fetch_and_add1: increment by 1 (inline, header). */
    AO_t val = 0;
    AO_fetch_and_add1(&val);
    CHECK(val == 1);

    /* 2. AO_fetch_and_add: full fetch-and-add path. */
    AO_t prev = AO_fetch_and_add(&val, 4);
    CHECK(prev == 1);
    CHECK(val == 5);

    /* 3. AO_store / AO_load round-trip. */
    AO_t cell = 42;
    AO_store(&cell, 99);
    CHECK(AO_load(&cell) == 99);

    /* 4. AO_compare_and_swap: expect success then failure. */
    CHECK(AO_compare_and_swap(&cell, 99, 100) == 1);
    CHECK(AO_load(&cell) == 100);
    CHECK(AO_compare_and_swap(&cell, 99, 101) == 0);
    CHECK(AO_load(&cell) == 100);

    /* 5. AO_test_and_set_acquire / AO_CLEAR lifecycle. */
    AO_TS_t ts = AO_TS_CLEAR;
    CHECK(AO_test_and_set_acquire(&ts) == AO_TS_CLEAR);
    CHECK(ts != AO_TS_CLEAR);
    AO_CLEAR(&ts);
    CHECK(ts == AO_TS_CLEAR);

    /* 6. AO_pause: exported from libatomic_ops (link check). */
    AO_pause();

    /* 7. AO_malloc / AO_free: exported from libatomic_ops_gpl. */
    void *p = AO_malloc(128);
    CHECK(p != NULL);
    AO_free(p);

    /* 8. AO_stack_push / AO_stack_pop: lock-free stack from the GPL lib.
       Link field (AO_uintptr_t) must be the first member, per upstream
       tests/test_stack.c. 7.10.0 has no AO_malloc_atomic /
       AO_stack_is_empty, so allocate with AO_malloc and test emptiness
       via pop returning NULL. */
    {
        struct stack_node { AO_uintptr_t link; int data; };
        AO_stack_t stack = AO_STACK_INITIALIZER;
        struct stack_node *node =
            (struct stack_node *)AO_malloc(sizeof(struct stack_node));
        CHECK(node != NULL);
        node->data = 1234;
        AO_stack_push(&stack, &node->link);
        {
            AO_uintptr_t *popped = AO_stack_pop(&stack);
            CHECK(popped == &node->link);
            CHECK(((struct stack_node *)popped)->data == 1234);
        }
        AO_free(node);
        CHECK(AO_stack_pop(&stack) == 0);
    }

    printf("libatomic-ops 7.10.0: all atomic operations tests passed\n");
    return 0;
}
