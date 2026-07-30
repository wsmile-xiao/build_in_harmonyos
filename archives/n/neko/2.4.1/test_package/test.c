/* test_package: consumer-side verification for the Neko shared library.
 *
 * Compile-time: include <neko.h>, verify macro expansion and type definitions.
 * Link-time:   link against libneko (libneko.so), verify VEXTERN symbols exist.
 * Run-time:    validate library exposes val_null/val_true/val_false singletons
 *              and that alloc_int / val_int macros produce correct results.
 *              (GC is auto-initialized by the shared library's constructor.)
 */

#include <stdio.h>
#include <stdlib.h>
#include <neko.h>

int main(void)
{
    int failures = 0;

    /* ---- 1. val_null singleton ---- */
    if (!val_is_null(val_null)) {
        fprintf(stderr, "FAIL: val_null is not null\n");
        failures++;
    }

    /* ---- 2. val_true / val_false ---- */
    if (val_true == val_false) {
        fprintf(stderr, "FAIL: val_true == val_false\n");
        failures++;
    }
    if (!val_is_bool(val_true)) {
        fprintf(stderr, "FAIL: val_true is not bool\n");
        failures++;
    }
    if (val_bool(val_false)) {
        fprintf(stderr, "FAIL: val_bool(val_false) != 0\n");
        failures++;
    }

    /* ---- 3. alloc_int / val_int round-trip ---- */
    value v42 = alloc_int(42);
    if (val_is_null(v42)) {
        fprintf(stderr, "FAIL: alloc_int(42) returned null\n");
        failures++;
    }
    if (!val_is_int(v42)) {
        fprintf(stderr, "FAIL: alloc_int(42) is not int\n");
        failures++;
    }
    if (val_int(v42) != 42) {
        fprintf(stderr, "FAIL: val_int(alloc_int(42)) != 42\n");
        failures++;
    }

    /* ---- 4. Negative integer ---- */
    value vNeg = alloc_int(-7);
    if (val_is_null(vNeg)) {
        fprintf(stderr, "FAIL: alloc_int(-7) returned null\n");
        failures++;
    }
    if (!val_is_int(vNeg)) {
        fprintf(stderr, "FAIL: alloc_int(-7) is not int\n");
        failures++;
    }
    if (val_int(vNeg) != -7) {
        fprintf(stderr, "FAIL: val_int(alloc_int(-7)) != -7\n");
        failures++;
    }

    /* ---- 5. val_is_null works on non-null int ---- */
    if (val_is_null(v42)) {
        fprintf(stderr, "FAIL: val_is_null(alloc_int(42)) true\n");
        failures++;
    }

    /* ---- 6. Link-time VEXTERN symbols are available ---- */
    /* val_null, val_true, val_false are VEXTERN globals from libneko.so.
     * The fact that we reach this line means the dynamic linker resolved them. */

    if (failures > 0) {
        fprintf(stderr, "test_neko FAILED with %d error(s)\n", failures);
        return 1;
    }

    printf("test_neko: all Neko C API checks passed\n");
    return 0;
}
