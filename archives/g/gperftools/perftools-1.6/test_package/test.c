#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* Real consumer smoke test for gperftools (tcmalloc).  Exercises the
 * tcmalloc_minimal API plus basic allocation behaviour so that a dead or
 * broken allocator link fails the test (R34). */
void* tc_malloc(size_t size);
void tc_free(void* ptr);

int main(void) {
    /* Link-level check: symbol must resolve via -ltcmalloc_minimal */
    void* p = tc_malloc(100);
    if (p == NULL) {
        printf("FAIL: tc_malloc returned NULL\n");
        return 1;
    }
    memset(p, 0xAB, 100);
    if (*(unsigned char*)p != 0xAB) {
        printf("FAIL: memory not writable\n");
        return 1;
    }
    tc_free(p);

    /* Plain malloc/free through the replaced allocator */
    void* q = malloc(4096);
    if (q == NULL) {
        printf("FAIL: malloc returned NULL\n");
        return 1;
    }
    memset(q, 0, 4096);
    free(q);

    printf("test gperftools perftools-1.6: OK\n");
    return 0;
}