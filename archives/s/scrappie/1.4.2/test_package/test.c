/* R34-compliant test: exercise the real scrappie matrix API.
 * Round-trip float arrays through scrappie's aligned matrix structure
 * (mat_from_array / array_from_scrappie_matrix) and verify values. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include <scrappie_matrix.h>

int main(void) {
    static const float x[15] = {
        1.0f, -2.5f, 3.25f, 0.0f, 7.0f,
        -1.5f, 2.0f, 4.5f, -6.0f, 8.125f,
        0.5f, 9.0f, -3.0f, 1.75f, 2.5f
    };
    const size_t nr = 3, nc = 5;

    scrappie_matrix mat = mat_from_array(x, nr, nc);
    if (mat == NULL) {
        fprintf(stderr, "FAIL: mat_from_array returned NULL\n");
        return 1;
    }
    if (mat->nr != nr || mat->nc != nc) {
        fprintf(stderr, "FAIL: matrix dimensions %zu x %zu, expected %zu x %zu\n",
                mat->nr, mat->nc, nr, nc);
        free_scrappie_matrix(mat);
        return 1;
    }

    float *y = array_from_scrappie_matrix(mat);
    if (y == NULL) {
        fprintf(stderr, "FAIL: array_from_scrappie_matrix returned NULL\n");
        free_scrappie_matrix(mat);
        return 1;
    }
    for (size_t i = 0; i < nr * nc; ++i) {
        if (fabsf(x[i] - y[i]) > 1e-6f) {
            fprintf(stderr, "FAIL: element %zu: %f != %f\n", i, x[i], y[i]);
            free(y);
            free_scrappie_matrix(mat);
            return 1;
        }
    }

    free(y);
    free_scrappie_matrix(mat);
    printf("scrappie 1.4.2 test_package: matrix round-trip OK\n");
    return 0;
}
