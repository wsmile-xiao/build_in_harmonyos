#include <sybdb.h>
#include <stdio.h>

int main(void) {
    /* Initialize FreeTDS db-lib library */
    if (dbinit() != SUCCEED) {
        fprintf(stderr, "dbinit() failed\n");
        return 1;
    }
    /* Verify library version */
    printf("FreeTDS version: %s\n", dbversion());
    /* Clean up */
    dbexit();
    return 0;
}
