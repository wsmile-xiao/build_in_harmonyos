/*
 * test_tcl_private_headers.c — formal consumer regression test.
 *
 * Compiles against Tcl private headers shipped inside the Conan package
 * (include/generic + include/unix) and links against libtcl8.6, proving the
 * packaged private-header layout is usable by C consumers (e.g. Expect).
 *
 * Assertions (runtime):
 *   A1: TCL_MAJOR_VERSION/TCL_MINOR_VERSION macros present (>= 8)
 *   A2: Tcl_CreateInterp succeeds
 *   A3: Tcl_Eval "expr {6 * 7}" returns 42
 */
#include <tclInt.h>
#include <tclPort.h>
#include <tclUnixPort.h>
#include <stdio.h>
#include <string.h>

#ifndef TCL_MAJOR_VERSION
#error "TCL_MAJOR_VERSION missing from tclInt.h"
#endif

int main(void) {
    if (TCL_MAJOR_VERSION < 8) {
        printf("[FAIL] TCL_MAJOR_VERSION = %d < 8\n", TCL_MAJOR_VERSION);
        return 1;
    }
    printf("[PASS] private headers define Tcl %d.%d\n",
           TCL_MAJOR_VERSION, TCL_MINOR_VERSION);

    Tcl_Interp *interp = Tcl_CreateInterp();
    if (interp == NULL) {
        printf("[FAIL] Tcl_CreateInterp returned NULL\n");
        return 1;
    }
    printf("[PASS] Tcl_CreateInterp succeeded\n");

    if (Tcl_Eval(interp, "expr {6 * 7}") != TCL_OK) {
        printf("[FAIL] Tcl_Eval expr failed: %s\n", Tcl_GetStringResult(interp));
        Tcl_DeleteInterp(interp);
        return 1;
    }
    if (strcmp(Tcl_GetStringResult(interp), "42") != 0) {
        printf("[FAIL] expr result = %s (expected 42)\n", Tcl_GetStringResult(interp));
        Tcl_DeleteInterp(interp);
        return 1;
    }
    printf("[PASS] Tcl_Eval 'expr {6 * 7}' = %s\n", Tcl_GetStringResult(interp));
    Tcl_DeleteInterp(interp);

    printf("=== Private header consumer OK (3 assertions) ===\n");
    return 0;
}
