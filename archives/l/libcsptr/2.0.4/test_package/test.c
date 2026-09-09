#include <stdio.h>
#include <stdlib.h>

#include "csptr/smart_ptr.h"
#include "csptr/smalloc.h"

/* Consumer test: actually allocates through libcsptr's smalloc-backed
 * smart pointer API (unique_ptr macro -> smalloc) and verifies value
 * round-trip, then frees via sfree.  NOTE: declare WITHOUT the `smart`
 * cleanup attribute because we free explicitly (upstream tests do the
 * same when calling sfree() manually). */
int main(void) {
    int *a = unique_ptr(int, 42);
    if (!a) {
        fprintf(stderr, "libcsptr: unique_ptr returned NULL\n");
        return 1;
    }
    if (*a != 42) {
        fprintf(stderr, "libcsptr: value mismatch, got %d expected 42\n", *a);
        return 1;
    }
    /* verify the meta accessor is linkable and returns NULL (no metadata) */
    if (get_smart_ptr_meta(a) != NULL) {
        fprintf(stderr, "libcsptr: unexpected metadata on plain unique_ptr\n");
        return 1;
    }
    sfree(a);
    printf("test libcsptr 2.0.4: OK\n");
    return 0;
}
