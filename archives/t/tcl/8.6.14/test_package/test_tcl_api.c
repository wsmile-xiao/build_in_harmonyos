/**
 * test_tcl_api.c — C API test for Tcl 8.6.14
 *
 * Compiles against <tcl.h> and links -ltcl8.6.
 * Exercises: Tcl_CreateInterp, Tcl_Eval, Tcl_DeleteInterp.
 */
#include <tcl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    int rc = 0;

    /* --- Test 1: Tcl_CreateInterp --- */
    Tcl_Interp *interp = Tcl_CreateInterp();
    if (!interp) {
        fprintf(stderr, "[FAIL] Tcl_CreateInterp returned NULL\n");
        return 1;
    }
    printf("[PASS] Tcl_CreateInterp succeeded\n");

    /* --- Test 2: Tcl_Eval basic expression --- */
    if (Tcl_Eval(interp, "expr {40 + 2}") != TCL_OK) {
        fprintf(stderr, "[FAIL] Tcl_Eval 'expr {40 + 2}' failed: %s\n",
                Tcl_GetStringResult(interp));
        rc = 1;
        goto cleanup;
    }
    const char *res = Tcl_GetStringResult(interp);
    if (strcmp(res, "42") != 0) {
        fprintf(stderr, "[FAIL] expr {40 + 2} = '%s', expected '42'\n", res);
        rc = 1;
        goto cleanup;
    }
    printf("[PASS] Tcl_Eval 'expr {40 + 2}' = %s\n", res);

    /* --- Test 3: Tcl_Eval info patchlevel --- */
    if (Tcl_Eval(interp, "puts [info patchlevel]") != TCL_OK) {
        fprintf(stderr, "[FAIL] Tcl_Eval 'info patchlevel' failed: %s\n",
                Tcl_GetStringResult(interp));
        rc = 1;
        goto cleanup;
    }
    printf("[PASS] Tcl_Eval 'info patchlevel' succeeded\n");

    /* --- Test 4: Tcl_Eval list operation --- */
    if (Tcl_Eval(interp, "llength {a b c}") != TCL_OK) {
        fprintf(stderr, "[FAIL] Tcl_Eval 'llength {a b c}' failed: %s\n",
                Tcl_GetStringResult(interp));
        rc = 1;
        goto cleanup;
    }
    res = Tcl_GetStringResult(interp);
    if (strcmp(res, "3") != 0) {
        fprintf(stderr, "[FAIL] llength {a b c} = '%s', expected '3'\n", res);
        rc = 1;
        goto cleanup;
    }
    printf("[PASS] Tcl_Eval 'llength {a b c}' = %s\n", res);

cleanup:
    Tcl_DeleteInterp(interp);
    if (rc == 0) {
        printf("\n=== All C API tests passed (4 assertions) ===\n");
    }
    return rc;
}
