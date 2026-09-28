/*
 * test_package/test.c — R34 test for guile 2.2.7
 *
 * Compiles and links against libguile-2.2, then evaluates Scheme (+ 1 2)
 * via the C API to verify the library is functional.
 *
 * Note: We use forward declarations instead of including strports.h and
 * numbers.h directly, because those headers pull in transitive deps
 * (ports.h for scm_t_port_type, gmp.h for GMP types) that require
 * system include paths not available in a pure conan environment.
 * The forward declarations are sufficient for R34 compile+link check.
 */
#include <libguile/__scm.h>
#include <libguile/threads.h>      /* scm_with_guile */

/* Forward declarations from libguile (avoid transitive header deps) */
extern SCM scm_c_eval_string(const char *expr);   /* from strports.h */
extern int scm_to_int32(SCM val);                  /* from numbers.h (scm_to_int is a macro → scm_to_int32) */

#include <stdio.h>
#include <stdlib.h>

static void *inner_main(void *data)
{
    SCM result = scm_c_eval_string("(+ 1 2)");
    int val = scm_to_int32(result);
    printf("guile test: (+ 1 2) = %d\n", val);
    fflush(stdout);
    if (val != 3) {
        fprintf(stderr, "FAIL: expected 3, got %d\n", val);
        return (void *)1;
    }
    printf("guile test: PASS\n");
    return NULL;
}

int main(void)
{
    void *status = scm_with_guile(inner_main, NULL);
    return status == NULL ? EXIT_SUCCESS : EXIT_FAILURE;
}
