#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <tcl.h>

int main(void) {
    /* Initialize Tcl */
    Tcl_FindExecutable("tclsh");
    Tcl_Interp *interp = Tcl_CreateInterp();
    if (!interp) {
        fprintf(stderr, "FAIL: Tcl_CreateInterp returned NULL\n");
        return 1;
    }

    /* Initialize standard Tcl commands (expr, concat, set, etc.) */
    if (Tcl_Init(interp) != TCL_OK) {
        fprintf(stderr, "FAIL: Tcl_Init failed: %s\n", Tcl_GetStringResult(interp));
        Tcl_DeleteInterp(interp);
        return 1;
    }

    /* Print Tcl version */
    const char *version = Tcl_GetVar(interp, "tcl_version", TCL_GLOBAL_ONLY);
    if (version != NULL) {
        printf("Tcl version: %s\n", version);
    } else {
        printf("Tcl version: (unknown)\n");
    }
    const char *patch_level = Tcl_GetVar(interp, "tcl_patchLevel", TCL_GLOBAL_ONLY);
    if (patch_level == NULL || strcmp(patch_level, "8.6.16") != 0) {
        fprintf(stderr, "FAIL: Tcl patch level \"%s\" != \"8.6.16\"\n",
                patch_level ? patch_level : "(NULL)");
        Tcl_DeleteInterp(interp);
        return 1;
    }
    printf("Tcl patch level: %s\n", patch_level);

    /* Evaluate a simple Tcl script */
    int rc = Tcl_Eval(interp, "expr 2 + 3");
    if (rc != TCL_OK) {
        fprintf(stderr, "FAIL: Tcl_Eval failed: %s\n", Tcl_GetStringResult(interp));
        Tcl_DeleteInterp(interp);
        return 1;
    }
    const char *expr_result = Tcl_GetStringResult(interp);
    printf("expr 2 + 3 = %s\n", expr_result);
    if (expr_result == NULL || strcmp(expr_result, "5") != 0) {
        fprintf(stderr, "FAIL: expr result \"%s\" != \"5\"\n",
                expr_result ? expr_result : "(NULL)");
        Tcl_DeleteInterp(interp);
        return 1;
    }

    /* Run another script — verify both rc and result content */
    rc = Tcl_Eval(interp, "concat hello world");
    if (rc != TCL_OK) {
        fprintf(stderr, "FAIL: Tcl_Eval(concat) failed: %s\n", Tcl_GetStringResult(interp));
        Tcl_DeleteInterp(interp);
        return 1;
    }
    const char *concat_result = Tcl_GetStringResult(interp);
    printf("concat test: %s\n", concat_result);
    /* concat hello world → "hello world" — verify content to catch silent regressions */
    if (concat_result == NULL || strcmp(concat_result, "hello world") != 0) {
        fprintf(stderr, "FAIL: concat result \"%s\" != \"hello world\"\n",
                concat_result ? concat_result : "(NULL)");
        Tcl_DeleteInterp(interp);
        return 1;
    }

    /* Clean up */
    Tcl_DeleteInterp(interp);
    printf("Smoke test PASSED.\n");
    return 0;
}
