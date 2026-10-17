#include <stdio.h>
#include "picosat.h"

int main(void) {
    int failures = 0;

    const char *version = picosat_version();
    printf("picosat version: %s\n", version ? version : "(null)");
    if (version == 0) {
        printf("FAIL: picosat_version returned NULL\n");
        failures++;
    }

    PicoSAT *sat = picosat_init();
    if (sat == 0) {
        printf("FAIL: picosat_init returned NULL\n");
        return 1;
    }
    picosat_add(sat, 1);
    picosat_add(sat, 0);
    int res = picosat_sat(sat, -1);
    printf("SAT case result: %d (expect %d)\n", res, PICOSAT_SATISFIABLE);
    if (res != PICOSAT_SATISFIABLE) {
        printf("FAIL: single-clause (x1) problem not SATISFIABLE\n");
        failures++;
    }
    int val = picosat_deref(sat, 1);
    printf("deref(1) in SAT case: %d (expect 1)\n", val);
    if (val != 1) {
        printf("FAIL: picosat_deref(1) should be 1 in SAT model\n");
        failures++;
    }
    int vars = picosat_variables(sat);
    printf("variables: %d (expect >= 1)\n", vars);
    if (vars < 1) {
        printf("FAIL: picosat_variables should be at least 1\n");
        failures++;
    }
    picosat_reset(sat);

    PicoSAT *unsat = picosat_init();
    if (unsat == 0) {
        printf("FAIL: second picosat_init returned NULL\n");
        return 1;
    }
    picosat_add(unsat, 1);
    picosat_add(unsat, 0);
    picosat_add(unsat, -1);
    picosat_add(unsat, 0);
    res = picosat_sat(unsat, -1);
    printf("UNSAT case result: %d (expect %d)\n", res, PICOSAT_UNSATISFIABLE);
    if (res != PICOSAT_UNSATISFIABLE) {
        printf("FAIL: (x1) AND (-x1) problem not UNSATISFIABLE\n");
        failures++;
    }
    picosat_reset(unsat);

    if (failures == 0) {
        printf("picosat consumer test: OK (7 checks passed)\n");
        return 0;
    }
    printf("picosat consumer test: %d check(s) failed\n", failures);
    return 1;
}
