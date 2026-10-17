#include <stdio.h>
#include <chibi/sexp.h>
#include <chibi/eval.h>

int main(void) {
    sexp ctx;
    sexp result;

    ctx = sexp_make_context(NULL, 0, 0);
    if (sexp_exceptionp(ctx)) {
        fprintf(stderr, "Failed to create context\n");
        return 1;
    }

    sexp_load_standard_env(ctx, NULL, SEXP_SEVEN);
    if (sexp_exceptionp(ctx)) {
        fprintf(stderr, "Failed to load standard environment\n");
    sexp env = sexp_load_standard_env(ctx, NULL, SEXP_SEVEN);
    if (sexp_exceptionp(env)) {
        fprintf(stderr, "Failed to load standard environment\n");
        return 1;
    }
    }

    result = sexp_eval_string(ctx, "(+ 1 2)", -1, sexp_context_env(ctx));
    if (sexp_exceptionp(result)) {
        fprintf(stderr, "Evaluation failed\n");
        return 1;
    }

    if (sexp_fixnump(result) && sexp_unbox_fixnum(result) == 3) {
        printf("chibi-scheme test: (+ 1 2) = 3 -- PASS\n");
        return 0;
    }

    fprintf(stderr, "chibi-scheme test: expected 3, got different result\n");
    return 1;
}
