#include <libgcab.h>
#include <glib.h>
#include <stdio.h>

int main(void) {
    /* Test: create a new GCabCabinet object */
    GCabCabinet *cabinet = gcab_cabinet_new();
    if (cabinet == NULL) {
        fprintf(stderr, "FAIL: gcab_cabinet_new() returned NULL\n");
        return 1;
    }
    printf("PASS: gcab_cabinet_new() succeeded\n");

    /* Test: check the type */
    if (!GCAB_IS_CABINET(cabinet)) {
        fprintf(stderr, "FAIL: GCAB_IS_CABINET check failed\n");
        g_object_unref(cabinet);
        return 1;
    }
    printf("PASS: GCAB_IS_CABINET check passed\n");

    g_object_unref(cabinet);
    printf("All tests passed\n");
    return 0;
}
