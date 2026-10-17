#include <gc/gc.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Initialize the garbage collector */
    GC_INIT();

    /* Allocate memory using GC - it should be automatically collected */
    char *p = (char *)GC_MALLOC(128);
    if (!p) {
        fprintf(stderr, "GC_MALLOC failed\n");
        return 1;
    }
    strcpy(p, "bdw-gc test");
    printf("GC_MALLOC: %s\n", p);

    /* Allocate more memory to trigger potential collection */
    for (int i = 0; i < 1000; i++) {
        char *tmp = (char *)GC_MALLOC(1024);
        if (!tmp) {
            fprintf(stderr, "GC_MALLOC failed at iteration %d\n", i);
            return 1;
        }
        memset(tmp, 0, 1024);
    }

    /* Trigger a garbage collection cycle */
    GC_gcollect();

    printf("bdw-gc 8.2.6 test: OK\n");
    return 0;
}
