#include <isl/ctx.h>
#include <isl/set.h>
#include <isl/val.h>
#include <isl/version.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *version = isl_version();
    /* isl_version() returns strings like "isl-0.28"; accept any containing 0.28. */
    if (version == NULL || strstr(version, "0.28") == NULL) {
        printf("unexpected isl version: %s\n", version ? version : "(null)");
        fflush(stdout);
        return 1;
    }

    isl_ctx *ctx = isl_ctx_alloc();
    if (ctx == NULL) {
        return 2;
    }

    isl_basic_set *bset =
        isl_basic_set_read_from_str(ctx, "{ [i] : 0 <= i <= 41 }");
    if (bset == NULL) {
        isl_ctx_free(ctx);
        return 3;
    }
    if (isl_basic_set_is_empty(bset) != isl_bool_false) {
        isl_basic_set_free(bset);
        isl_ctx_free(ctx);
        return 4;
    }

    isl_set *set = isl_set_from_basic_set(bset);
    isl_val *count = isl_set_count_val(set);
    long n = isl_val_get_num_si(count);
    isl_val_free(count);
    if (n != 42) {
        isl_ctx_free(ctx);
        return 5;
    }

    isl_basic_set *empty =
        isl_basic_set_read_from_str(ctx, "{ [i] : 1 = 0 }");
    if (empty == NULL) {
        isl_ctx_free(ctx);
        return 6;
    }
    if (isl_basic_set_is_empty(empty) != isl_bool_true) {
        isl_basic_set_free(empty);
        isl_ctx_free(ctx);
        return 7;
    }
    isl_basic_set_free(empty);

    printf("libisl %s result: 42\n", version);
    fflush(stdout);
    isl_ctx_free(ctx);
    return 0;
}
