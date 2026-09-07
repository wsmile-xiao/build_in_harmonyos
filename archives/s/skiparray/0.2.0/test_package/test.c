#include <skiparray.h>
#include <stdint.h>

static int compare_ints(const void *a, const void *b, void *udata) {
    int left = *(const int *)a;
    int right = *(const int *)b;
    (void)udata;
    return (left > right) - (left < right);
}

int main(void) {
    struct skiparray_config config = {0};
    struct skiparray *array = NULL;
    struct skiparray_pair pair = {0};
    void *value = NULL;
    void *first_key = NULL;
    void *first_value = NULL;
    void *last_key = NULL;
    void *last_value = NULL;
    int key1 = 1, key2 = 2, key3 = 3;
    int value1 = 10, value2 = 20, value3 = 30;

    config.cmp = compare_ints;
    if (skiparray_new(&config, &array) != SKIPARRAY_NEW_OK || !array) return 1;
    if (skiparray_set(array, &key2, &value2) != SKIPARRAY_SET_BOUND) return 2;
    if (skiparray_set(array, &key1, &value1) != SKIPARRAY_SET_BOUND) return 3;
    if (skiparray_set(array, &key3, &value3) != SKIPARRAY_SET_BOUND) return 4;
    if (skiparray_count(array) != 3) return 5;
    if (!skiparray_member(array, &key2)) return 6;
    if (!skiparray_get(array, &key2, &value) || value != &value2) return 7;
    if (skiparray_first(array, &first_key, &first_value) != SKIPARRAY_FIRST_OK ||
        first_key != &key1 || first_value != &value1) return 8;
    if (skiparray_last(array, &last_key, &last_value) != SKIPARRAY_LAST_OK ||
        last_key != &key3 || last_value != &value3) return 9;
    if (skiparray_forget(array, &key2, &pair) != SKIPARRAY_FORGET_OK ||
        pair.key != &key2 || pair.value != &value2) return 10;
    if (skiparray_count(array) != 2) return 11;
    if (skiparray_pop_first(array, &first_key, &first_value) != SKIPARRAY_POP_OK ||
        first_key != &key1 || first_value != &value1) return 12;
    if (skiparray_count(array) != 1) return 13;
    skiparray_free(array);
    return 0;
}
