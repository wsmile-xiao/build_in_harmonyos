/* Consumer test for libambix: exercises real library API.
 *
 * Six ordered checks (stdout lines "CHECK <n> OK" are the harness evidence;
 * any failure prints to stderr and exits 1 so the harness detects it):
 *   1. ambix_order2channels() full-set channel counts
 *   2. ambix_channels2order() inverse mapping (incl. non-full-set => -1)
 *   3. ambix_is_fullset() predicates
 *   4. matrix init + identity fill + element verification
 *   5. matrix fill_data + multiply_float32 on a known 2x2 case
 *   6. matrix copy + create/destroy lifecycle
 */
#include <ambix/ambix.h>

#include <stdio.h>

#define CHECK(cond, n, label)                                          \
    do {                                                               \
        if (!(cond)) {                                                 \
            fprintf(stderr, "CHECK %d FAILED: %s\n", (n), (label));    \
            return 1;                                                  \
        }                                                              \
        printf("CHECK %d OK: %s\n", (n), (label));                     \
    } while (0)

int main(void) {
    /* 1: order -> channels: (order+1)^2 */
    CHECK(ambix_order2channels(0) == 1, 1, "order2channels(0)==1");
    CHECK(ambix_order2channels(1) == 4, 1, "order2channels(1)==4");
    CHECK(ambix_order2channels(2) == 9, 1, "order2channels(2)==9");
    CHECK(ambix_order2channels(3) == 16, 1, "order2channels(3)==16");

    /* 2: channels -> order, -1 when not a full set */
    CHECK(ambix_channels2order(1) == 0, 2, "channels2order(1)==0");
    CHECK(ambix_channels2order(4) == 1, 2, "channels2order(4)==1");
    CHECK(ambix_channels2order(9) == 2, 2, "channels2order(9)==2");
    CHECK(ambix_channels2order(3) == -1, 2, "channels2order(3)==-1");

    /* 3: full-set predicates */
    CHECK(ambix_is_fullset(1) != 0, 3, "is_fullset(1)");
    CHECK(ambix_is_fullset(4) != 0, 3, "is_fullset(4)");
    CHECK(ambix_is_fullset(16) != 0, 3, "is_fullset(16)");
    CHECK(ambix_is_fullset(2) == 0, 3, "!is_fullset(2)");
    CHECK(ambix_is_fullset(5) == 0, 3, "!is_fullset(5)");

    /* 4: identity matrix round-trip through init/fill */
    {
        ambix_matrix_t *mtx = ambix_matrix_init(2, 2, NULL);
        CHECK(mtx != NULL, 4, "matrix_init(2,2) non-NULL");
        CHECK(mtx->rows == 2 && mtx->cols == 2, 4, "matrix dims 2x2");
        CHECK(ambix_matrix_fill(mtx, AMBIX_MATRIX_IDENTITY) == mtx, 4,
              "matrix_fill IDENTITY");
        CHECK(mtx->data[0][0] == 1.0f && mtx->data[1][1] == 1.0f, 4,
              "identity diagonal==1");
        CHECK(mtx->data[0][1] == 0.0f && mtx->data[1][0] == 0.0f, 4,
              "identity off-diagonal==0");
        ambix_matrix_destroy(mtx);
    }

    /* 5: fill_data + multiply_float32: diag(2,3) * [4,5] == [8,15] */
    {
        ambix_matrix_t *mtx = ambix_matrix_init(2, 2, NULL);
        const float32_t data[4] = {2.0f, 0.0f, 0.0f, 3.0f};
        const float32_t src[2] = {4.0f, 5.0f};
        float32_t dest[2] = {0.0f, 0.0f};
        CHECK(mtx != NULL, 5, "scale matrix init non-NULL");
        CHECK(ambix_matrix_fill_data(mtx, data) == AMBIX_ERR_SUCCESS, 5,
              "matrix_fill_data success");
        CHECK(ambix_matrix_multiply_float32(dest, mtx, src, 1) ==
                  AMBIX_ERR_SUCCESS,
              5, "matrix_multiply_float32 success");
        CHECK(dest[0] == 8.0f && dest[1] == 15.0f, 5,
              "scale multiply result [8,15]");
        ambix_matrix_destroy(mtx);
    }

    /* 6: copy + create/destroy lifecycle */
    {
        ambix_matrix_t *src = ambix_matrix_init(1, 3, NULL);
        ambix_matrix_t *dst = NULL;
        ambix_matrix_t *empty = NULL;
        CHECK(src != NULL, 6, "1x3 matrix init non-NULL");
        CHECK(ambix_matrix_fill(src, AMBIX_MATRIX_ONE) == src, 6,
              "matrix_fill ONE");
        dst = ambix_matrix_copy(src, NULL);
        CHECK(dst != NULL, 6, "matrix_copy non-NULL");
        CHECK(dst->rows == 1 && dst->cols == 3, 6, "copy dims 1x3");
        CHECK(dst->data[0][0] == 1.0f && dst->data[0][2] == 1.0f, 6,
              "copy data all ones");
        empty = ambix_matrix_create();
        CHECK(empty != NULL, 6, "matrix_create non-NULL");
        CHECK(empty->rows == 0 && empty->cols == 0, 6, "fresh matrix empty");
        ambix_matrix_destroy(src);
        ambix_matrix_destroy(dst);
        ambix_matrix_destroy(empty);
    }

    printf("ALL CHECKS PASSED: 6/6\n");
    return 0;
}
