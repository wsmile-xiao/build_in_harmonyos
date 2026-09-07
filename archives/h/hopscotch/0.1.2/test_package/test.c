#include <hopscotch.h>
#include <stdint.h>
#include <stdio.h>

static void group(uint32_t id, size_t count, const uint32_t *members, void *udata)
{
    size_t *seen = (size_t *)udata;
    (void)id;
    (void)members;
    if (count == 2) (*seen)++;
}

int main(void)
{
    struct hopscotch *t = hopscotch_new();
    const uint32_t a[] = {2};
    const uint32_t b[] = {1};
    size_t seen = 0;
    if (!t || !hopscotch_add(t, 1, 1, a) || !hopscotch_add(t, 2, 1, b) ||
        !hopscotch_seal(t) || !hopscotch_solve(t, 0, group, &seen)) {
        hopscotch_free(t);
        return 1;
    }
    hopscotch_free(t);
    if (seen != 1) {
        fprintf(stderr, "expected one two-node component, got %zu\n", seen);
        return 2;
    }
    puts("hopscotch API consumer: OK");
    return 0;
}
