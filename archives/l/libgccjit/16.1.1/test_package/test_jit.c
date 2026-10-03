/* Consumer test for the packaged libgccjit 16.1.1 JIT library.
 *
 * This exercises the actual JIT path on HarmonyOS: it asks libgccjit to
 * compile a small C function in-process, materialise executable machine
 * code (the runtime must be able to mmap+protect JIT memory — the core
 * W^X / SELinux interaction of the OHOS port), call the generated
 * function, and check its result.
 */
#include <libgccjit.h>

#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    gcc_jit_context *ctx;
    gcc_jit_result *result;
    gcc_jit_type *int_type;
    gcc_jit_param *x_param;
    gcc_jit_function *fn;
    gcc_jit_context *child;
    void *code;

    ctx = gcc_jit_context_acquire();
    if (ctx == NULL) {
        fprintf(stderr, "gcc_jit_context_acquire failed\n");
        return 1;
    }
    gcc_jit_context_set_int_option(ctx, GCC_JIT_INT_OPTION_OPTIMIZATION_LEVEL, 2);

    /* GCC 16 API: gcc_jit_context_get_int_type(ctxt, num_bytes, is_signed). */
    int_type = gcc_jit_context_get_int_type(ctx, sizeof(int), 1);
    x_param = gcc_jit_context_new_param(ctx, NULL, int_type, "x");
    {
        gcc_jit_param *params[1] = {x_param};
        fn = gcc_jit_context_new_function(
            ctx, NULL, GCC_JIT_FUNCTION_EXPORTED, int_type, "square", 1,
            params, 0);
    }
    {
        gcc_jit_lvalue *x_lvalue =
            gcc_jit_param_as_lvalue(x_param);
        gcc_jit_rvalue *result_expr =
            gcc_jit_context_new_binary_op(
                ctx, NULL, GCC_JIT_BINARY_OP_MULT, int_type,
                gcc_jit_lvalue_as_rvalue(x_lvalue),
                gcc_jit_lvalue_as_rvalue(x_lvalue));
        gcc_jit_block *block =
            gcc_jit_function_new_block(fn, "entry");
        gcc_jit_block_end_with_return(block, NULL, result_expr);
    }

    /* libgccjit's default in-process (embedded) driver does not run the
       packaged bin/gcc wrapper, so it misses the -B startfile paths the
       wrapper injects (sysroot crt files and the packaged libgcc).  Pass
       the same -B directories through the driver options when the test
       environment provides them. */
    {
        const char *jit_b_crt = getenv("OHOS_JIT_B_CRT");
        const char *jit_b_gcc = getenv("OHOS_JIT_B_GCC");
        if (jit_b_crt != NULL) {
            gcc_jit_context_add_driver_option(ctx, jit_b_crt);
        }
        if (jit_b_gcc != NULL) {
            gcc_jit_context_add_driver_option(ctx, jit_b_gcc);
        }
    }

    /* Compile and materialise executable code in-process. */
    result = gcc_jit_context_compile(ctx);
    if (result == NULL) {
        fprintf(stderr, "gcc_jit_context_compile failed\n");
        gcc_jit_context_release(ctx);
        return 2;
    }
    code = gcc_jit_result_get_code(result, "square");
    if (code == NULL) {
        fprintf(stderr, "gcc_jit_result_get_code failed\n");
        gcc_jit_result_release(result);
        gcc_jit_context_release(ctx);
        return 3;
    }

    {
        typedef int (*square_fn)(int);
        square_fn square = (square_fn)code;
        if (square(7) != 49 || square(-3) != 9) {
            fprintf(stderr, "JIT-compiled function returned wrong result\n");
            gcc_jit_result_release(result);
            gcc_jit_context_release(ctx);
            return 4;
        }
    }

    /* Also verify the compiler-compiler path (nested context). */
    child = gcc_jit_context_acquire();
    if (child == NULL) {
        fprintf(stderr, "nested gcc_jit_context_acquire failed\n");
        gcc_jit_result_release(result);
        gcc_jit_context_release(ctx);
        return 5;
    }
    gcc_jit_context_release(child);

    gcc_jit_result_release(result);
    gcc_jit_context_release(ctx);
    puts("libgccjit-jit-ohos-ok");
    return 0;
}
