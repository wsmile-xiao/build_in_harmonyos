#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "matrix.h"

/* Consumer test: use the public matrix_hub C API like a real upstream
 * application would.  Builds two matrices, multiplies them, verifies the
 * result numerically and via the exported print routine. */
int main(void) {
    MATRIX_TYPE a_data[4] = {1.0, 2.0, 3.0, 4.0};
    MATRIX_TYPE b_data[4] = {5.0, 6.0, 7.0, 8.0};
    /* A*B = [19 22; 43 50] */
    MATRIX_TYPE expected[4] = {19.0, 22.0, 43.0, 50.0};
    int rc = 1;

    Matrix *A = Matrix_gen(2, 2, a_data);
    Matrix *B = Matrix_gen(2, 2, b_data);
    if (!A || !B) {
        fprintf(stderr, "FAIL: Matrix_gen returned NULL\n");
        return 1;
    }

    Matrix *C = M_mul(A, B);
    if (!C) {
        fprintf(stderr, "FAIL: M_mul returned NULL\n");
        goto out;
    }
    if (C->row != 2 || C->column != 2) {
        fprintf(stderr, "FAIL: wrong shape %dx%d\n", C->row, C->column);
        goto out;
    }
    for (int i = 0; i < 4; i++) {
        if (C->data[i] != expected[i]) {
            fprintf(stderr, "FAIL: C[%d] = %f, expected %f\n",
                    i, (double)C->data[i], (double)expected[i]);
            goto out;
        }
    }
    printf("M_mul verified: A*B = ");
    M_print(C);

    Matrix *I = M_I(2);
    if (!I || I->data[0] != 1.0 || I->data[1] != 0.0 ||
        I->data[2] != 0.0 || I->data[3] != 1.0) {
        fprintf(stderr, "FAIL: M_I(2) identity check\n");
        goto out;
    }
    printf("M_I verified: ");
    M_print(I);

    printf("test matrix_hub consumer: OK\n");
    rc = 0;

out:
    if (C) M_free(C);
    if (I) M_free(I);
    if (A) M_free(A);
    if (B) M_free(B);
    return rc;
}