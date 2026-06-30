#include <stdio.h>
#include "boolector/boolector.h"

int main(void) {
    Btor *btor = boolector_new();
    BoolectorSort bv8 = boolector_bitvec_sort(btor, 8);
    BoolectorNode *x = boolector_var(btor, bv8, "x");
    BoolectorNode *zero = boolector_zero(btor, bv8);
    BoolectorNode *ult_x = boolector_ult(btor, zero, x);
    boolector_assert(btor, ult_x);

    int result = boolector_sat(btor);
    if (result == BOOLECTOR_SAT) {
        printf("sat\n");
    } else {
        printf("unsat\n");
    }

    boolector_release(btor, x);
    boolector_release(btor, zero);
    boolector_release(btor, ult_x);
    boolector_release_sort(btor, bv8);
    boolector_delete(btor);
    return 0;
}
