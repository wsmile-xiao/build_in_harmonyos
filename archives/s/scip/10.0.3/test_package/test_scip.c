/*
 * SCIP consumer smoke test — creates a SCIP environment, builds and solves
 * a simple LP problem, verifying the library and LP solver (SoPlex) work.
 */
#include <scip/scip.h>
#include <scip/scipdefplugins.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    SCIP* scip = NULL;
    SCIP_RETCODE ret;
    SCIP_VAR* var = NULL;
    SCIP_CONS* cons = NULL;
    SCIP_Real optimal_value;

    /* 1. Create SCIP environment */
    ret = SCIPcreate(&scip);
    if (ret != SCIP_OKAY) {
        fprintf(stderr, "SCIPcreate failed\n");
        return 1;
    }

    /* 2. Include default plugins (LP solver, heuristics, etc.) */
    ret = SCIPincludeDefaultPlugins(scip);
    if (ret != SCIP_OKAY) {
        fprintf(stderr, "SCIPincludeDefaultPlugins failed\n");
        SCIPfree(&scip);
        return 1;
    }

    /* 3. Create a problem */
    ret = SCIPcreateProb(scip, "test", NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    if (ret != SCIP_OKAY) {
        fprintf(stderr, "SCIPcreateProb failed\n");
        SCIPfree(&scip);
        return 1;
    }

    /* 4. Create a variable: x in [0, 10], objective coefficient 1.0 */
    ret = SCIPcreateVar(scip, &var, "x", 0.0, 10.0, 1.0,
                        SCIP_VARTYPE_CONTINUOUS, TRUE, NULL, NULL, NULL, NULL, NULL);
    if (ret != SCIP_OKAY) {
        fprintf(stderr, "SCIPcreateVar failed\n");
        SCIPfree(&scip);
        return 1;
    }
    ret = SCIPaddVar(scip, var);
    if (ret != SCIP_OKAY) {
        fprintf(stderr, "SCIPaddVar failed\n");
        SCIPreleaseVar(scip, &var);
        SCIPfree(&scip);
        return 1;
    }

    /* 5. Add constraint: x <= 5 */
    SCIP_Real coeffs[] = {1.0};
    SCIP_VAR* vars[] = {var};
    ret = SCIPcreateConsLinear(scip, &cons, "c1", 1, vars, coeffs,
                               -SCIPinfinity(scip), 5.0,
                               TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE);
    if (ret != SCIP_OKAY) {
        fprintf(stderr, "SCIPcreateConsLinear failed\n");
        SCIPreleaseVar(scip, &var);
        SCIPfree(&scip);
        return 1;
    }
    ret = SCIPaddCons(scip, cons);
    if (ret != SCIP_OKAY) {
        fprintf(stderr, "SCIPaddCons failed\n");
        SCIPreleaseCons(scip, &cons);
        SCIPreleaseVar(scip, &var);
        SCIPfree(&scip);
        return 1;
    }

    /* 6. Solve the problem (maximize x subject to x <= 5) */
    ret = SCIPsolve(scip);
    if (ret != SCIP_OKAY) {
        fprintf(stderr, "SCIPsolve failed\n");
        SCIPreleaseCons(scip, &cons);
        SCIPreleaseVar(scip, &var);
        SCIPfree(&scip);
        return 1;
    }

    /* 7. Check the solution: optimal x = 5.0 */
    if (SCIPgetNSols(scip) == 0) {
        fprintf(stderr, "No solution found\n");
        SCIPreleaseCons(scip, &cons);
        SCIPreleaseVar(scip, &var);
        SCIPfree(&scip);
        return 1;
    }

    optimal_value = SCIPgetPrimalbound(scip);
    /* The optimal objective value should be 5.0 (maximize x with x <= 5) */
    if (optimal_value < 4.9 || optimal_value > 5.1) {
        fprintf(stderr, "Unexpected optimal value: %f (expected 5.0)\n", optimal_value);
        SCIPreleaseCons(scip, &cons);
        SCIPreleaseVar(scip, &var);
        SCIPfree(&scip);
        return 1;
    }

    printf("SCIP test: OK (solved LP, optimal value = %.1f, LP solver = %s)\n",
           optimal_value, SCIPgetLPSName(scip));

    /* 8. Cleanup */
    SCIPreleaseCons(scip, &cons);
    SCIPreleaseVar(scip, &var);
    SCIPfree(&scip);

    /* 9. Check for memory leaks */
    if (SCIPgetMemUsed(scip) > 0) {
        fprintf(stderr, "Warning: memory not fully freed\n");
    }

    return 0;
}
