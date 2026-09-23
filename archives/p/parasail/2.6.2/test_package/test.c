/* test_package for parasail 2.6.2 on OHOS (aarch64).
 *
 * Verifies, against the actually installed library:
 *   - runtime version function agrees with the header version macros;
 *   - generic dispatcher parasail_nw computes the upstream-documented
 *     score for the classic "asdf"/"asdf" blosum62 case (same semantics
 *     as upstream tests/test_basic.c test1);
 *   - a SIMD 128-bit striped kernel (16-bit) computes an identity-matrix
 *     self-alignment score of the full sequence length;
 *   - the NEON backend (compiled on aarch64 per configure) is linked in
 *     and dispatchable.
 */
#include <stdio.h>
#include <stdlib.h>

#include <parasail.h>
#include <parasail/matrices/blosum62.h>

int main(void) {
    int failures = 0;
    int major = 0, minor = 0, patch = 0;
    parasail_result_t *result = NULL;
    parasail_matrix_t *matrix = NULL;

    /* Runtime version must agree with header macros (2.6.2). */
    parasail_version(&major, &minor, &patch);
    if (major != PARASAIL_VERSION_MAJOR) {
        fprintf(stderr, "FAIL: runtime major %d != header %d\n",
                major, PARASAIL_VERSION_MAJOR);
        failures++;
    }
    if (minor != PARASAIL_VERSION_MINOR) {
        fprintf(stderr, "FAIL: runtime minor %d != header %d\n",
                minor, PARASAIL_VERSION_MINOR);
        failures++;
    }
    if (patch != PARASAIL_VERSION_PATCH) {
        fprintf(stderr, "FAIL: runtime patch %d != header %d\n",
                patch, PARASAIL_VERSION_PATCH);
        failures++;
    }
    if (major != 2 || minor != 6 || patch != 2) {
        fprintf(stderr, "FAIL: version is not 2.6.2 (%d.%d.%d)\n",
                major, minor, patch);
        failures++;
    }

    /* Generic dispatcher, upstream test_basic.c test1 semantics:
     * parasail_nw("asdf", 4, "asdf", 4, 10, 1, blosum62) == 20. */
    result = parasail_nw("asdf", 4, "asdf", 4, 10, 1, &parasail_blosum62);
    if (result == NULL) {
        fprintf(stderr, "FAIL: parasail_nw returned NULL\n");
        failures++;
    } else {
        if (result->score != 20) {
            fprintf(stderr, "FAIL: parasail_nw score %d != 20\n",
                    result->score);
            failures++;
        }
        if (result->end_query != 3 || result->end_ref != 3) {
            fprintf(stderr, "FAIL: parasail_nw ends (%d,%d) != (3,3)\n",
                    result->end_query, result->end_ref);
            failures++;
        }
        parasail_result_free(result);
        result = NULL;
    }

    /* SIMD 128-bit striped 16-bit kernel with a simple identity matrix:
     * self-alignment of "acgtacgt" (8 residues, match=1) scores 8. */
    matrix = parasail_matrix_create("acgt", 1, -1);
    if (matrix == NULL) {
        fprintf(stderr, "FAIL: parasail_matrix_create returned NULL\n");
        failures++;
    } else {
        result = parasail_nw_striped_16("acgtacgt", 8, "acgtacgt", 8,
                                        10, 1, matrix);
        if (result == NULL) {
            fprintf(stderr, "FAIL: parasail_nw_striped_16 returned NULL\n");
            failures++;
        } else {
            if (result->score != 8) {
                fprintf(stderr,
                        "FAIL: parasail_nw_striped_16 score %d != 8\n",
                        result->score);
                failures++;
            }
            parasail_result_free(result);
            result = NULL;
        }

        /* NEON backend: on aarch64 configure compiles the NEON kernels;
         * the symbol must be present and callable. */
        result = parasail_nw_striped_neon_128_16("acgtacgt", 8, "acgtacgt",
                                                 8, 10, 1, matrix);
        if (result == NULL) {
            fprintf(stderr,
                    "FAIL: parasail_nw_striped_neon_128_16 returned NULL\n");
            failures++;
        } else {
            if (result->score != 8) {
                fprintf(stderr,
                        "FAIL: neon_128 score %d != 8\n", result->score);
                failures++;
            }
            parasail_result_free(result);
            result = NULL;
        }
        parasail_matrix_free(matrix);
        matrix = NULL;
    }

    if (failures != 0) {
        fprintf(stderr, "test_package: %d check(s) FAILED\n", failures);
        return EXIT_FAILURE;
    }
    printf("test_package: all checks passed (parasail %d.%d.%d)\n",
           PARASAIL_VERSION_MAJOR, PARASAIL_VERSION_MINOR,
           PARASAIL_VERSION_PATCH);
    return EXIT_SUCCESS;
}
