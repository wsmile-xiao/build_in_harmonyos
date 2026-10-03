#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "range_list.h"

int main(void) {
    range_list *list = range_list_new();
    assert(list != NULL);
    assert(range_list_add(list, 0, 5, (void *)(uintptr_t)1));
    assert(range_list_add(list, 10, 5, (void *)(uintptr_t)2));
    assert(range_list_size(list) == 2);
    assert(range_list_find(list, 2) == 0);
    assert(range_list_find(list, 12) == 1);
    assert(range_list_find(list, 7) < 0);
    assert(!range_list_add(list, 4, 3, NULL));
    range_list_free(list);
    puts("REGLOOKUP_RANGE_LIST_PASS");
    return 0;
}
