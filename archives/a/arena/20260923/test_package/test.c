#include <stdio.h>
#include <string.h>

/* arena is an stb-style single-file library:
 * consumer defines ARENA_IMPLEMENTATION and includes the header. */
#define ARENA_IMPLEMENTATION
#include "arena.h"

int main(void)
{
    Arena a = {0};
    int rc = 0;

    /* arena_alloc: allocate and write observable data */
    int *p = arena_alloc(&a, sizeof(int) * 4);
    if (!p) { printf("arena_alloc returned NULL\n"); rc = 1; goto out; }
    for (int i = 0; i < 4; i++) p[i] = i * 10;
    printf("arena_alloc[3]=%d\n", p[3]);        /* expect 30 */

    /* arena_sprintf: printf-style into arena memory */
    char *s = arena_sprintf(&a, "arena says %s (%d)", "hi", 42);
    if (!s) { printf("arena_sprintf returned NULL\n"); rc = 1; goto out; }
    printf("arena_sprintf=%s\n", s);            /* expect arena says hi (42) */
    if (strcmp(s, "arena says hi (42)") != 0) rc = 1;

    /* arena_reset / rewind / free must not crash */
    arena_reset(&a);
    arena_free(&a);

out:
    if (rc == 0) printf("test arena 20260923: OK\n");
    return rc;
}
