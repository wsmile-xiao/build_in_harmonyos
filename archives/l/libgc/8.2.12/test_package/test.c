#include <gc/gc.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int passed = 0;

    /* Initialize the garbage collector */
    GC_INIT();

    /* CHECK 1: GC_MALLOC + content verification */
    {
        char *p = (char *)GC_MALLOC(128);
        if (!p) {
            fprintf(stderr, "CHECK 1: FAIL (GC_MALLOC returned NULL)\n");
            return 1;
        }
        strcpy(p, "libgc test");
        if (strcmp(p, "libgc test") != 0) {
            fprintf(stderr, "CHECK 1: FAIL (content mismatch)\n");
            return 1;
        }
        printf("CHECK 1: PASS (GC_MALLOC basic allocation)\n");
        passed++;
    }

    /* CHECK 2: GC_REALLOC preserves content and grows */
    {
        char *p = (char *)GC_MALLOC(64);
        if (!p) {
            fprintf(stderr, "CHECK 2: FAIL (GC_MALLOC returned NULL)\n");
            return 1;
        }
        strcpy(p, "realloc-check");
        char *q = (char *)GC_REALLOC(p, 1024);
        if (!q) {
            fprintf(stderr, "CHECK 2: FAIL (GC_REALLOC returned NULL)\n");
            return 1;
        }
        if (strcmp(q, "realloc-check") != 0) {
            fprintf(stderr, "CHECK 2: FAIL (realloc content mismatch)\n");
            return 1;
        }
        memset(q + 64, 0xAB, 960);
        printf("CHECK 2: PASS (GC_REALLOC preserves content)\n");
        passed++;
    }

    /* CHECK 3: GC_STRDUP + explicit collection cycle */
    {
        const char *orig = "libgc-8.2.12 strdup check";
        char *dup = GC_STRDUP(orig);
        if (!dup) {
            fprintf(stderr, "CHECK 3: FAIL (GC_STRDUP returned NULL)\n");
            return 1;
        }
        if (strcmp(dup, orig) != 0) {
            fprintf(stderr, "CHECK 3: FAIL (strdup mismatch)\n");
            return 1;
        }
        /* Allocate churn to trigger potential collection, then collect */
        for (int i = 0; i < 1000; i++) {
            char *tmp = (char *)GC_MALLOC(1024);
            if (!tmp) {
                fprintf(stderr, "CHECK 3: FAIL (churn alloc %d)\n", i);
                return 1;
            }
            memset(tmp, 0, 1024);
        }
        GC_gcollect();
        if (strcmp(dup, orig) != 0) {
            fprintf(stderr, "CHECK 3: FAIL (reachable object collected)\n");
            return 1;
        }
        printf("CHECK 3: PASS (GC_STRDUP + GC_gcollect keeps reachable)\n");
        passed++;
    }

    printf("libgc 8.2.12 test: %d/3 CHECKs passed: OK\n", passed);
    return passed == 3 ? 0 : 1;
}
