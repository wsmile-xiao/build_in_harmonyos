#include <isl/ctx.h>
#include <isl/val.h>

#include <stdio.h>

int main(void)
{
    isl_ctx *ctx = isl_ctx_alloc();
    isl_val *value;
    int ok;

    if (ctx == NULL) {
        return 1;
    }
    value = isl_val_int_from_si(ctx, 42);
    ok = value != NULL && isl_val_is_int(value) && isl_val_get_num_si(value) == 42;
    isl_val_free(value);
    isl_ctx_free(ctx);

    if (!ok) {
        return 1;
    }
    puts("isl25 functional checks passed: 3");
    return 0;
}
