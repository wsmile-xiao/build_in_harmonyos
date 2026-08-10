#include <jemalloc/jemalloc.h>
#include <stdio.h>

int main(void) {
    /* R34: Test jemalloc's malloc/free (statically linked override) */
    void *ptr = malloc(1024);
    if (!ptr) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }
    free(ptr);
    printf("jemalloc test: OK\n");
    return 0;
}
