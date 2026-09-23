/* Consumer test for the packaged liblrcalc (CI L1, R34).
 *
 * Builds partitions through the exported vector API and checks three
 * Littlewood-Richardson coefficients whose values were verified against
 * the packaged `lrcalc coef` executable (upstream testsuite/README).
 */
#include <stdio.h>

#include <lrcalc/symfcn.h>
#include <lrcalc/vector.h>

static int failures;

static void check_lrcoef(const char *name, vector *outer, vector *inner1,
                         vector *inner2, long long expected)
{
    long long value = lrcoef(outer, inner1, inner2);
    if (value != expected) {
        printf("FAIL %s: got %lld expected %lld\n", name, value, expected);
        failures++;
    } else {
        printf("ok %s: %lld\n", name, value);
    }
}

int main(void)
{
    vector *v321 = v_new_init(3, 3, 2, 1);
    vector *v21 = v_new_init(2, 2, 1);
    vector *v3 = v_new_init(1, 3);
    vector *v4321 = v_new_init(4, 4, 3, 2, 1);
    vector *v32 = v_new_init(2, 3, 2);

    check_lrcoef("c^{321}_{21,21}", v321, v21, v21, 2);
    check_lrcoef("c^{321}_{3,21}", v321, v3, v21, 1);
    check_lrcoef("c^{4321}_{32,21}", v4321, v32, v21, 0);

    v_free1(v321);
    v_free1(v21);
    v_free1(v3);
    v_free1(v4321);
    v_free1(v32);

    if (failures) {
        printf("%d checks FAILED\n", failures);
        return 1;
    }
    printf("ALL_OK: 3 lrcoef checks passed\n");
    return 0;
}
