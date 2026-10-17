#include <stdio.h>
#include <stdlib.h>

#include "pqueue.h"

typedef struct node_t
{
    pqueue_pri_t pri;
    int    val;
    size_t pos;
} node_t;

static int
cmp_pri(pqueue_pri_t next, pqueue_pri_t curr)
{
    return (next < curr);
}

static pqueue_pri_t
get_pri(void *a)
{
    return ((node_t *) a)->pri;
}

static void
set_pri(void *a, pqueue_pri_t pri)
{
    ((node_t *) a)->pri = pri;
}

static size_t
get_pos(void *a)
{
    return ((node_t *) a)->pos;
}

static void
set_pos(void *a, size_t pos)
{
    ((node_t *) a)->pos = pos;
}

int
main(void)
{
    pqueue_t *pq;
    node_t   *ns;
    node_t   *n;
    int       ok = 1;

    ns = malloc(10 * sizeof(node_t));
    pq = pqueue_init(10, cmp_pri, get_pri, set_pri, get_pos, set_pos);
    if (!(ns && pq)) {
        fprintf(stderr, "pqueue_init failed\n");
        return 1;
    }

    ns[0].pri = 5; ns[0].val = -5; pqueue_insert(pq, &ns[0]);
    ns[1].pri = 4; ns[1].val = -4; pqueue_insert(pq, &ns[1]);
    ns[2].pri = 2; ns[2].val = -2; pqueue_insert(pq, &ns[2]);
    ns[3].pri = 6; ns[3].val = -6; pqueue_insert(pq, &ns[3]);
    ns[4].pri = 1; ns[4].val = -1; pqueue_insert(pq, &ns[4]);

    if (pqueue_size(pq) != 5) {
        fprintf(stderr, "size mismatch: %zu\n", pqueue_size(pq));
        ok = 0;
    }

    n = pqueue_peek(pq);
    if (!n || n->pri != 6 || n->val != -6) {
        fprintf(stderr, "peek mismatch\n");
        ok = 0;
    }
    printf("peek: %llu [%d]\n", n->pri, n->val);

    pqueue_change_priority(pq, 8, &ns[4]);
    pqueue_change_priority(pq, 7, &ns[2]);

    {
        pqueue_pri_t expected[5] = {8, 7, 6, 5, 4};
        int i = 0;
        while ((n = pqueue_pop(pq))) {
            printf("pop: %llu [%d]\n", n->pri, n->val);
            if (n->pri != expected[i]) {
                fprintf(stderr, "pop %d mismatch: %llu != %llu\n",
                        i, n->pri, expected[i]);
                ok = 0;
            }
            i++;
        }
        if (i != 5) {
            fprintf(stderr, "pop count mismatch: %d\n", i);
            ok = 0;
        }
    }

    pqueue_free(pq);
    free(ns);

    if (!ok) {
        fprintf(stderr, "test libpqueue 09b72d55c4: FAILED\n");
        return 1;
    }
    printf("test libpqueue 09b72d55c4: OK\n");
    return 0;
}
