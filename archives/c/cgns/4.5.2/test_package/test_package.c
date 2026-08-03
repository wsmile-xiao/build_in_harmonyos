#include <stdio.h>
#include <cgnslib.h>
#include <stdlib.h>

int main(void) {
    int ier;
    int fn;
    char filename[] = "test_cgns.cgns";
    int nbases = 0;

    /* Step 1: Create a new CGNS file */
    ier = cg_open(filename, CG_MODE_WRITE, &fn);
    if (ier != CG_OK) {
        fprintf(stderr, "FAIL: cg_open(CG_MODE_WRITE) returned %d\n", ier);
        return 1;
    }
    printf("PASS: cg_open(CG_MODE_WRITE) = %d, fn=%d\n", ier, fn);

    /* Write a CGNS base node */
    int cell_dim = 3, phys_dim = 3;
    int base_id;
    ier = cg_base_write(fn, "Base", cell_dim, phys_dim, &base_id);
    if (ier != CG_OK) {
        fprintf(stderr, "FAIL: cg_base_write returned %d\n", ier);
        cg_close(fn);
        return 1;
    }
    printf("PASS: cg_base_write = %d, base_id=%d\n", ier, base_id);

    /* Close the file */
    ier = cg_close(fn);
    if (ier != CG_OK) {
        fprintf(stderr, "FAIL: cg_close returned %d\n", ier);
        return 1;
    }
    printf("PASS: cg_close = %d\n", ier);

    /* Step 2: Reopen the file in read-only mode to verify */
    ier = cg_open(filename, CG_MODE_READ, &fn);
    if (ier != CG_OK) {
        fprintf(stderr, "FAIL: cg_open(CG_MODE_READ) returned %d\n", ier);
        return 1;
    }
    printf("PASS: cg_open(CG_MODE_READ) = %d, fn=%d\n", ier, fn);

    /* Verify the base node exists */
    ier = cg_nbases(fn, &nbases);
    if (ier != CG_OK || nbases < 1) {
        fprintf(stderr, "FAIL: cg_nbases returned %d, nbases=%d\n", ier, nbases);
        cg_close(fn);
        return 1;
    }
    printf("PASS: cg_nbases = %d, nbases=%d\n", ier, nbases);

    ier = cg_close(fn);
    if (ier != CG_OK) {
        fprintf(stderr, "FAIL: cg_close (reopen) returned %d\n", ier);
        return 1;
    }
    printf("PASS: cg_close (reopen) = %d\n", ier);

    printf("\nAll CGNS API tests PASSED\n");
    return 0;
}
