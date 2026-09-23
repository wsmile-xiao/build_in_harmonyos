#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "hashmap.h"

/* Real consumer test: exercise the public hashmap API end-to-end.
 * Insert/update/delete/get/count/scan via the exported header only.
 *
 * NOTE: hashmap_set() returns NULL on a *successful insert* (a non-NULL
 * return means an existing item was replaced).  Detect failure via
 * hashmap_oom() instead. */

typedef struct {
    char name[32];
    int age;
} Person;

static uint64_t person_hash(const void *item, uint64_t seed0, uint64_t seed1) {
    const Person *p = item;
    return hashmap_sip(p->name, strlen(p->name), seed0, seed1);
}

static int person_compare(const void *a, const void *b, void *udata) {
    const Person *pa = a, *pb = b;
    return strcmp(pa->name, pb->name);
}

int main(void) {
    struct hashmap *map = hashmap_new(sizeof(Person), 0, 0, 0,
                                      person_hash, person_compare, NULL, NULL);
    if (!map) { fprintf(stderr, "hashmap_new failed\n"); return 1; }

    Person alice = {"alice", 30};
    Person bob = {"bob", 25};

    hashmap_set(map, &alice);
    if (hashmap_oom(map)) { fprintf(stderr, "set alice OOM\n"); return 1; }
    hashmap_set(map, &bob);
    if (hashmap_oom(map)) { fprintf(stderr, "set bob OOM\n"); return 1; }
    if (hashmap_count(map) != 2) { fprintf(stderr, "count != 2\n"); return 1; }

    const Person *got = hashmap_get(map, &bob);
    if (!got || got->age != 25) { fprintf(stderr, "get bob failed\n"); return 1; }

    alice.age = 31; /* update: replaces existing item, returns old item ptr */
    const void *old = hashmap_set(map, &alice);
    if (!old) { fprintf(stderr, "update alice did not replace\n"); return 1; }
    got = hashmap_get(map, &alice);
    if (!got || got->age != 31) { fprintf(stderr, "update alice failed\n"); return 1; }

    if (hashmap_delete(map, &alice) == NULL) { fprintf(stderr, "delete alice failed\n"); return 1; }
    if (hashmap_count(map) != 1) { fprintf(stderr, "count != 1 after delete\n"); return 1; }

    size_t iter = 0;
    void *item;
    int scanned = 0;
    while (hashmap_iter(map, &iter, &item)) { scanned++; }
    if (scanned != 1) { fprintf(stderr, "iter count != 1\n"); return 1; }

    hashmap_free(map);
    printf("hashmap consumer test PASSED\n");
    return 0;
}
