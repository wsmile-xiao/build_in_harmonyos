/*
 * test_package consumer test for sljit 0.0-git20260924.b706c11.
 *
 * Genuinely exercises the packaged JIT library: it asks sljit to compile
 * a three-argument integer addition function at run time, calls the
 * generated machine code with five input vectors and verifies the results.
 * If the code generator, executable allocator, or calling convention is
 * broken the assertions fail and the test exits non-zero.
 */
#include "sljitLir.h"

#include <stdio.h>
#include <stdlib.h>

typedef sljit_sw(SLJIT_FUNC *func3_t)(sljit_sw a, sljit_sw b, sljit_sw c);

static func3_t compile_add3(void)
{
    struct sljit_compiler *compiler = sljit_create_compiler(NULL);
    void *code;

    if (!compiler) {
        fprintf(stderr, "FAIL create: sljit_create_compiler returned NULL\n");
        return NULL;
    }

    sljit_emit_enter(compiler, 0,
        SLJIT_ARGS3(W, W, W, W),
        1, 3, 0);
    sljit_emit_op1(compiler, SLJIT_MOV, SLJIT_R0, 0, SLJIT_S0, 0);
    sljit_emit_op2(compiler, SLJIT_ADD, SLJIT_R0, 0, SLJIT_R0, 0, SLJIT_S1, 0);
    sljit_emit_op2(compiler, SLJIT_ADD, SLJIT_R0, 0, SLJIT_R0, 0, SLJIT_S2, 0);
    sljit_emit_return(compiler, SLJIT_MOV, SLJIT_R0, 0);

    code = sljit_generate_code(compiler, 0, NULL);
    sljit_free_compiler(compiler);
    if (!code) {
        fprintf(stderr, "FAIL generate: sljit_generate_code returned NULL\n");
        return NULL;
    }
    return (func3_t)code;
}

int main(void)
{
    static const struct { sljit_sw a, b, c, expect; } cases[] = {
        { 4, 5, 6, 15 },
        { 0, 0, 0, 0 },
        { -1, -2, -3, -6 },
        { 100, 200, 300, 600 },
        { -100, 50, 25, -25 },
    };
    func3_t func;
    int i;

    func = compile_add3();
    if (!func)
        return 1;

    for (i = 0; i < 5; i++) {
        sljit_sw got = func(cases[i].a, cases[i].b, cases[i].c);
        if (got != cases[i].expect) {
            fprintf(stderr, "FAIL case%d: add3(%ld,%ld,%ld) expected %ld got %ld\n",
                i, (long)cases[i].a, (long)cases[i].b, (long)cases[i].c,
                (long)cases[i].expect, (long)got);
            sljit_free_code((void *)func, NULL);
            return 1;
        }
    }

    sljit_free_code((void *)func, NULL);
    printf("sljit test_package ok\n");
    return 0;
}
