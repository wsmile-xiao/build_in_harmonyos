/* test_package/src/main.c — bsd-compat-headers consumer test.
 * Verifies that <sys/queue.h> and <sys/tree.h> are usable.
 */
#include <sys/queue.h>
#include <sys/tree.h>
#include <stdio.h>
#include <stdlib.h>

/* Test queue.h: LIST */
struct item {
    int value;
    LIST_ENTRY(item) entries;
};

LIST_HEAD(item_list, item);

/* Test tree.h: RB tree */
struct rb_item {
    int key;
    RB_ENTRY(rb_item) entry;
};

static int rb_cmp(const struct rb_item *a, const struct rb_item *b) {
    return (a->key < b->key) ? -1 : (a->key > b->key) ? 1 : 0;
}

RB_HEAD(rb_tree, rb_item);
RB_PROTOTYPE(rb_tree, rb_item, entry, rb_cmp);
RB_GENERATE(rb_tree, rb_item, entry, rb_cmp);

int main(void) {
    /* Test LIST */
    struct item_list list;
    LIST_INIT(&list);

    struct item a = { .value = 10 };
    struct item b = { .value = 20 };
    LIST_INSERT_HEAD(&list, &a, entries);
    LIST_INSERT_AFTER(&a, &b, entries);

    int sum = 0;
    struct item *p;
    LIST_FOREACH(p, &list, entries) {
        sum += p->value;
    }
    if (sum != 30) {
        fprintf(stderr, "FAIL: LIST sum = %d, expected 30\n", sum);
        return 1;
    }

    /* Test RB tree */
    struct rb_tree tree;
    RB_INIT(&tree);

    static struct rb_item items[5];
    int keys[] = {3, 1, 4, 1, 5};
    for (int i = 0; i < 5; i++) {
        items[i].key = keys[i];
        RB_INSERT(rb_tree, &tree, &items[i]);
    }

    /* Find min */
    struct rb_item *min = RB_MIN(rb_tree, &tree);
    if (!min || min->key != 1) {
        fprintf(stderr, "FAIL: RB_MIN key = %d\n", min ? min->key : -1);
        return 1;
    }

    /* Find max */
    struct rb_item *max = RB_MAX(rb_tree, &tree);
    if (!max || max->key != 5) {
        fprintf(stderr, "FAIL: RB_MAX key = %d\n", max ? max->key : -1);
        return 1;
    }

    printf("bsd-compat-headers smoke test: PASS (LIST + RB tree ok)\n");
    return 0;
}
