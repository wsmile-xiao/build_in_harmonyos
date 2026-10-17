/* test_package for primer3 2.6.1 — real API tests (R34).
 *
 * Links the packaged static libraries and exercises two core APIs:
 *   1. libprimer3: p3_create_global_settings() + p3_set_gs_primer_opt_size()
 *      (global primer settings handling — the heart of the library)
 *   2. oligotm:    oligotm() melting-temperature computation
 *
 * libprimer3.cc is compiled as C++11, therefore this C source is linked
 * with the C++ linker (see CMakeLists.txt LINKER_LANGUAGE CXX).
 */
#include <stdio.h>
#include <string.h>

#include "libprimer3.h"
#include "oligotm.h"

int main(void)
{
    /* ---- Test 1: libprimer3 global settings API ---- */
    p3_global_settings *gs = p3_create_global_settings();
    if (gs == NULL) {
        fprintf(stderr, "FAIL: p3_create_global_settings() returned NULL\n");
        return 1;
    }

    int orig_opt = gs->p_args.opt_size;
    if (orig_opt <= 0 || orig_opt > 100) {
        fprintf(stderr, "FAIL: implausible default PRIMER_OPT_SIZE=%d\n",
                orig_opt);
        return 1;
    }

    p3_set_gs_primer_opt_size(gs, 22);
    if (gs->p_args.opt_size != 22) {
        fprintf(stderr,
                "FAIL: p3_set_gs_primer_opt_size() had no effect (still %d)\n",
                gs->p_args.opt_size);
        return 1;
    }
    printf("libprimer3 API OK: default opt_size=%d, after set_gs_primer_opt_size(22): %d\n",
           orig_opt, gs->p_args.opt_size);

    /* ---- Test 2: oligotm melting temperature API ---- */
    const char *seq = "ACGATCGATCGATCGATCGATCGATCGATCGA";
    tm_ret tmr = oligotm(seq,
                         /*dna_conc*/ 50.0,
                         /*salt_conc*/ 50.0,
                         /*divalent_conc*/ 1.5,
                         /*dntp_conc*/ 0.6,
                         /*dmso_conc*/ 0.0,
                         /*dmso_fact*/ 0.6,
                         /*formamide_conc*/ 0.0,
                         santalucia_auto,
                         santalucia,
                         /*annealing_temp*/ 0.0);
    printf("oligotm API OK: Tm=%f bound=%f for %s\n", tmr.Tm, tmr.bound, seq);

    if (tmr.Tm == OLIGOTM_ERROR || tmr.Tm < 0.0 || tmr.Tm > 200.0) {
        fprintf(stderr, "FAIL: oligotm() returned implausible Tm=%f\n",
                tmr.Tm);
        return 1;
    }

    printf("ALL primer3 LIBRARY TESTS PASSED\n");
    return 0;
}
