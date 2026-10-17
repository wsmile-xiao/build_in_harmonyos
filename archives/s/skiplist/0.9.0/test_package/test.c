#include <skiplist.h>
#include <stdint.h>

static int compare_ints(void *a, void *b) {
    intptr_t left = (intptr_t)a;
    intptr_t right = (intptr_t)b;
    return left < right ? -1 : left > right ? 1 : 0;
}

int main(void) {
    struct skiplist *list = skiplist_new(compare_ints, NULL, NULL);
    if (list == NULL || !skiplist_add(list, (void *)3, (void *)30) ||
        !skiplist_add(list, (void *)1, (void *)10) ||
        !skiplist_set(list, (void *)2, (void *)20, NULL)) {
        if (list != NULL) skiplist_free(list, NULL, NULL);
        return 1;
    }
    if (skiplist_count(list) != 3 || !skiplist_member(list, (void *)2)) {
        skiplist_free(list, NULL, NULL);
        return 2;
    }
    void *value = NULL;
    if (!skiplist_get(list, (void *)2, &value) || (intptr_t)value != 20) {
        skiplist_free(list, NULL, NULL);
        return 3;
    }
    void *first_key = NULL;
    void *last_key = NULL;
    if (!skiplist_first(list, &first_key, NULL) || (intptr_t)first_key != 1 ||
        !skiplist_last(list, &last_key, NULL) || (intptr_t)last_key != 3) {
        skiplist_free(list, NULL, NULL);
        return 4;
    }
    if (!skiplist_delete(list, (void *)2, &value) || (intptr_t)value != 20 ||
        skiplist_count(list) != 2) {
        skiplist_free(list, NULL, NULL);
        return 5;
    }
    if (skiplist_free(list, NULL, NULL) != 2) return 6;
    return 0;
}
