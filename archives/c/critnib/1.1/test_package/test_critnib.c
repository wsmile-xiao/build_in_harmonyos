#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "critnib.h"

static int seen_count;
static uintptr_t seen_sum;

static int count_cb(uintptr_t key, void *value, void *privdata)
{
    (void)value;
    (void)privdata;
    seen_count++;
    seen_sum += key;
    return 0;
}

int main(void)
{
    critnib *c = critnib_new();
    assert(c != NULL); /* 1: create */

    /* 2: insert three keys */
    assert(critnib_insert(c, 10, (void *)0xA, 0) == 0);
    assert(critnib_insert(c, 20, (void *)0x14, 0) == 0);
    assert(critnib_insert(c, 30, (void *)0x1E, 0) == 0);

    /* 3: equality lookup */
    assert(critnib_get(c, 20) == (void *)0x14);
    assert(critnib_get(c, 99) == NULL);

    /* 4: neighbour lookup (LE/GE) */
    assert(critnib_find_le(c, 25) == (void *)0x14);
    {
        uintptr_t rkey = 0;
        void *rval = NULL;
        assert(critnib_find(c, 25, FIND_GE, &rkey, &rval) == 1);
        assert(rkey == 30 && rval == (void *)0x1E);
    }

    /* 5: remove */
    assert(critnib_remove(c, 20) == (void *)0x14);
    assert(critnib_get(c, 20) == NULL);

    /* 6: iterate remaining [10, 30] -> keys 10 + 30 */
    seen_count = 0;
    seen_sum = 0;
    critnib_iter(c, 10, 30, count_cb, NULL);
    assert(seen_count == 2 && seen_sum == 40);

    critnib_delete(c);
    printf("critnib consumer test PASSED (6 assertions)\n");
    return 0;
}
