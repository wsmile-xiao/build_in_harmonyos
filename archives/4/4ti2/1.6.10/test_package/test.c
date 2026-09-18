/* test_package test source — verifies the 4ti2 C API (qsolve) on OHOS.
 * Mirrors upstream test/qsolve/api/qsolve_main.cpp: feeds the same constraint
 * system through the public C API and checks the computed "qhom" matrix
 * against upstream's expected output. Exits non-zero on any mismatch.
 */
#include <stdio.h>
#include "4ti2/4ti2.h"

int main(void)
{
    /* Input data (identical to upstream test/qsolve/api/qsolve_main.cpp). */
    const int m = 4;
    const int n = 3;
    _4ti2_int64_t mat[4][3] = {
        { 2,  3, -6 },
        { 2, -1, -4 },
        { 1,  2, -11 },
        { 1, -1,  1 }
    };
    _4ti2_int64_t rel[4] = { _4ti2_LB, _4ti2_UB, _4ti2_UB, _4ti2_LB };
    _4ti2_int64_t sign[3] = { _4ti2_LB, _4ti2_LB, _4ti2_LB };

    /* Expected output: qhom matrix (verified by the upstream test suite). */
    const int k = 4;
    _4ti2_int64_t qhom[4][3] = {
        { 3, 4, 1 },
        { 3, 8, 5 },
        { 9, 2, 4 },
        { 19, 18, 5 }
    };

    _4ti2_state *qsolve_api = _4ti2_qsolve_create_state(_4ti2_PREC_INT_64);
    if (qsolve_api == NULL) {
        fprintf(stderr, "FAIL: _4ti2_qsolve_create_state returned NULL\n");
        return 1;
    }

    _4ti2_matrix *cons_matrix = NULL;
    if (_4ti2_state_create_matrix(qsolve_api, m, n, "mat", &cons_matrix) != _4ti2_OK
            || cons_matrix == NULL) {
        fprintf(stderr, "FAIL: _4ti2_state_create_matrix(mat)\n");
        return 1;
    }
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < n; ++j) {
            _4ti2_matrix_set_entry_int64_t(cons_matrix, i, j, mat[i][j]);
        }
    }

    _4ti2_matrix *rel_matrix = NULL;
    if (_4ti2_state_create_matrix(qsolve_api, 1, m, "rel", &rel_matrix) != _4ti2_OK
            || rel_matrix == NULL) {
        fprintf(stderr, "FAIL: _4ti2_state_create_matrix(rel)\n");
        return 1;
    }
    for (int i = 0; i < m; ++i) {
        _4ti2_matrix_set_entry_int64_t(rel_matrix, 0, i, rel[i]);
    }

    _4ti2_matrix *sign_matrix = NULL;
    if (_4ti2_state_create_matrix(qsolve_api, 1, n, "sign", &sign_matrix) != _4ti2_OK
            || sign_matrix == NULL) {
        fprintf(stderr, "FAIL: _4ti2_state_create_matrix(sign)\n");
        return 1;
    }
    for (int j = 0; j < n; ++j) {
        _4ti2_matrix_set_entry_int64_t(sign_matrix, 0, j, sign[j]);
    }

    if (_4ti2_state_compute(qsolve_api) != _4ti2_OK) {
        fprintf(stderr, "FAIL: _4ti2_state_compute\n");
        return 1;
    }

    _4ti2_matrix *qhom_matrix = NULL;
    _4ti2_state_get_matrix(qsolve_api, "qhom", &qhom_matrix);
    if (qhom_matrix == NULL) {
        fprintf(stderr, "FAIL: _4ti2_state_get_matrix(qhom) returned NULL\n");
        return 1;
    }

    if (_4ti2_matrix_get_num_rows(qhom_matrix) != k) {
        fprintf(stderr, "FAIL: qhom rows = %d, expected %d\n",
                _4ti2_matrix_get_num_rows(qhom_matrix), k);
        return 1;
    }
    if (_4ti2_matrix_get_num_cols(qhom_matrix) != n) {
        fprintf(stderr, "FAIL: qhom cols = %d, expected %d\n",
                _4ti2_matrix_get_num_cols(qhom_matrix), n);
        return 1;
    }
    for (int i = 0; i < k; ++i) {
        for (int j = 0; j < n; ++j) {
            _4ti2_int64_t value = 0;
            _4ti2_matrix_get_entry_int64_t(qhom_matrix, i, j, &value);
            if (value != qhom[i][j]) {
                fprintf(stderr, "FAIL: qhom[%d][%d] = %lld, expected %lld\n",
                        i, j, (long long)value, (long long)qhom[i][j]);
                return 1;
            }
        }
    }

    _4ti2_state_delete(qsolve_api);
    printf("4ti2 qsolve C API test: PASSED (4x3 qhom matrix verified, 12 entries)\n");
    return 0;
}
