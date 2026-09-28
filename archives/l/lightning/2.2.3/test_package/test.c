/*
 * test_package consumer test for GNU lightning 2.2.3.
 *
 * Genuinely exercises the library's core JIT capability: it asks lightning
 * to compile two functions at run time (one returning a constant, one adding
 * two arguments), retrieves the generated machine-code addresses, calls them
 * and verifies the results.  If lightning's code generator is broken the
 * assertions fail and the test exits non-zero.
 */
#include <lightning.h>
#include <stdio.h>
#include <stdlib.h>

static jit_state_t *_jit;

typedef long (*func_void)(void);
typedef long (*func_ii)(long, long);

int main(void)
{
    jit_node_t *n_const;
    jit_node_t *n_add;
    func_void   f_const;
    func_ii     f_add;
    jit_node_t *a1;
    jit_node_t *a2;
    long        r;

    init_jit("test_lightning");
    _jit = jit_new_state();

    /* Function that returns a constant:  R0 = 0x13579bdf; return R0  */
    n_const = jit_name("const_value");
    jit_prolog();
    jit_movi(JIT_R0, 0x13579bdf);
    jit_retr(JIT_R0);
    jit_epilog();

    /* Function that returns the sum of two integer arguments.  */
    n_add = jit_name("add");
    jit_prolog();
    a1 = jit_arg_i();
    a2 = jit_arg_i();
    jit_getarg_i(JIT_R0, a1);
    jit_getarg_i(JIT_R1, a2);
    jit_addr(JIT_R0, JIT_R0, JIT_R1);
    jit_retr(JIT_R0);
    jit_epilog();

    /* Compile everything registered in this state.  */
    jit_emit();
    f_const = (func_void)jit_address(n_const);
    f_add = (func_ii)jit_address(n_add);

    jit_clear_state();

    r = f_const();
    if (r != 0x13579bdf) {
        fprintf(stderr, "FAIL const: expected %#lx got %#lx\n",
                0x13579bdfL, r);
        return 1;
    }
    r = f_add(20, 22);
    if (r != 42) {
        fprintf(stderr, "FAIL add: expected 42 got %ld\n", r);
        return 1;
    }
    r = f_add(-1, -1);
    if (r != -2) {
        fprintf(stderr, "FAIL add(neg): expected -2 got %ld\n", r);
        return 1;
    }
    r = f_add(1, 2);
    if (r != 3) {
        fprintf(stderr, "FAIL add: expected 3 got %ld\n", r);
        return 1;
    }

    jit_destroy_state();
    finish_jit();

    printf("lightning test_package ok\n");
    return 0;
}
