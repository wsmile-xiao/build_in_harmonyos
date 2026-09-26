/*
 * test_package consumer test for rayforce 2.8.1.
 *
 * Uses ONLY the installed public header (<rayforce.h>) and the linked
 * static library — a genuine third-party consumer of the package.
 * Exercises real public APIs and asserts observable results:
 *   - vector construction / append / data
 *   - table construction with a named column
 *   - null handling round-trip
 */
#include <rayforce.h>
#include <stdio.h>

static int fail(const char* what) {
    fprintf(stderr, "FAIL: %s\n", what);
    return 1;
}

int main(void) {
    (void)ray_sym_init();

    /* 1. I64 vector: build, append, inspect */
    int64_t vals[] = {10, 20, 30};
    ray_t* v = ray_vec_from_raw(RAY_I64, vals, 3);
    if (!v || RAY_IS_ERR(v)) return fail("ray_vec_from_raw");

    int64_t x = 40;
    v = ray_vec_append(v, &x);
    if (RAY_IS_ERR(v)) return fail("ray_vec_append");

    int64_t* d = (int64_t*)ray_data(v);
    if (d[0] != 10 || d[3] != 40) return fail("ray_data values");

    /* 2. Table: one named column, row count */
    ray_t* tbl = ray_table_new(1);
    if (!tbl || RAY_IS_ERR(tbl)) return fail("ray_table_new");
    int64_t name = ray_sym_intern("x", 1);
    tbl = ray_table_add_col(tbl, name, v);
    if (RAY_IS_ERR(tbl)) return fail("ray_table_add_col");
    if (ray_table_nrows(tbl) != 4) return fail("ray_table_nrows");

    ray_release(tbl);

    /* 3. Null handling: set a null, confirm it reads back as null */
    ray_t* v2 = ray_vec_from_raw(RAY_I64, vals, 3);
    if (!v2 || RAY_IS_ERR(v2)) return fail("ray_vec_from_raw v2");
    if (ray_vec_set_null_checked(v2, 1, true) != RAY_OK) return fail("set null");
    if (!ray_vec_is_null(v2, 1) || ray_vec_is_null(v2, 0)) return fail("null flags");

    ray_release(v2);

    printf("rayforce consumer test: OK\n");
    return 0;
}