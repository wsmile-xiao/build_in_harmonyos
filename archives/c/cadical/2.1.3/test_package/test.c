#include <ccadical.h>

#include <stdio.h>

static int add_clause(CCaDiCaL *solver, int first, int second)
{
    ccadical_add(solver, first);
    ccadical_add(solver, second);
    ccadical_add(solver, 0);
    return 0;
}

int main(void)
{
    const char *signature = ccadical_signature();
    CCaDiCaL *solver = NULL;
    int result;

    if (signature == NULL || signature[0] == '\0') {
        fprintf(stderr, "FAIL: ccadical_signature() is empty\n");
        return 1;
    }
    printf("CaDiCaL signature: %s\n", signature);

    solver = ccadical_init();
    if (solver == NULL) {
        fprintf(stderr, "FAIL: ccadical_init() returned NULL\n");
        return 1;
    }

    result = ccadical_solve(solver);
    if (result != 10) {
        fprintf(stderr, "FAIL: empty formula expected 10, got %d\n", result);
        ccadical_release(solver);
        return 1;
    }

    /* The clauses force the single model x1=false and x2=true. */
    add_clause(solver, -1, 2);
    add_clause(solver, 1, 2);
    add_clause(solver, -1, -2);

    result = ccadical_solve(solver);
    if (result != 10) {
        fprintf(stderr, "FAIL: satisfiable formula expected 10, got %d\n", result);
        ccadical_release(solver);
        return 1;
    }
    /*
     * 'ccadical_val' returns the satisfied signed literal itself, not a
     * -1/0/1 normalized value: upstream cadical.hpp documents
     * "Get value (-lit=false, lit=true)" and solver.cpp asserts
     * (res == lit || res == -lit) before returning.
     */
    int value1 = ccadical_val(solver, 1);
    int value2 = ccadical_val(solver, 2);
    if (value1 != -1 || value2 != 2) {
        fprintf(stderr, "FAIL: unexpected model values %d and %d\n", value1, value2);
        ccadical_release(solver);
        return 1;
    }
    ccadical_release(solver);

    solver = ccadical_init();
    if (solver == NULL) {
        fprintf(stderr, "FAIL: second ccadical_init() returned NULL\n");
        return 1;
    }
    ccadical_add(solver, 1);
    ccadical_add(solver, 0);
    ccadical_add(solver, -1);
    ccadical_add(solver, 0);

    result = ccadical_solve(solver);
    if (result != 20) {
        fprintf(stderr, "FAIL: contradictory formula expected 20, got %d\n", result);
        ccadical_release(solver);
        return 1;
    }
    ccadical_release(solver);

    printf("All CaDiCaL consumer tests passed.\n");
    return 0;
}
