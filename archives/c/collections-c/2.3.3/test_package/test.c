/* test.c — collections-c 2.3.3 consumer smoke test.
 * Exercises the real library API (R34): create an Array, add elements,
 * read back by index and size, then destroy. */
#include <stdio.h>
#include "cc_array.h"

int main(void) {
    CC_Array *ar = NULL;
    enum cc_stat s = cc_array_new(&ar);
    if (s != CC_OK) {
        fprintf(stderr, "cc_array_new failed: %d\n", s);
        return 1;
    }

    int a = 1, b = 2, c = 3;
    if (cc_array_add(ar, &a) != CC_OK ||
        cc_array_add(ar, &b) != CC_OK ||
        cc_array_add(ar, &c) != CC_OK) {
        fprintf(stderr, "cc_array_add failed\n");
        cc_array_destroy(ar);
        return 1;
    }

    size_t n = cc_array_size(ar);
    void *e = NULL;
    cc_array_get_at(ar, 1, &e);
    printf("size=%zu elem=%d\n", n, *(int *)e);

    cc_array_destroy(ar);
    return (n == 3 && *(int *)e == 2) ? 0 : 1;
}
