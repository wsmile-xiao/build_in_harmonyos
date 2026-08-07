#include <math.h>
#include <stdio.h>
#include <string.h>

#include <xc.h>

static int fail(const char *message)
{
    fprintf(stderr, "%s\n", message);
    return 1;
}

int main(void)
{
    int major = 0;
    int minor = 0;
    int micro = 0;
    const char *version = NULL;
    xc_func_type func;
    const xc_func_info_type *info = NULL;
    const double rho[3] = {0.1, 0.4, 1.0};
    double exc[3] = {0.0, 0.0, 0.0};
    const int func_id = 1;
    int rc;

    xc_version(&major, &minor, &micro);
    if (major != 7 || minor != 1 || micro != 0) {
        return fail("unexpected libxc version tuple");
    }

    version = xc_version_string();
    if (version == NULL || strstr(version, "7.1.0") == NULL) {
        return fail("unexpected libxc version string");
    }

    if (xc_number_of_functionals() <= 0) {
        return fail("functional inventory is empty");
    }

    rc = xc_func_init(&func, func_id, XC_UNPOLARIZED);
    if (rc != 0) {
        return fail("failed to initialize LDA exchange functional");
    }

    info = xc_func_get_info(&func);
    if (info == NULL || info->family != XC_FAMILY_LDA) {
        xc_func_end(&func);
        return fail("LDA exchange functional did not report the LDA family");
    }

    xc_lda_exc(&func, 3, rho, exc);
    if (!isfinite(exc[0]) || !isfinite(exc[1]) || !isfinite(exc[2])) {
        xc_func_end(&func);
        return fail("non-finite exchange energy density");
    }
    if (!(exc[0] < 0.0 && exc[1] < exc[0] && exc[2] < exc[1])) {
        xc_func_end(&func);
        return fail("unexpected LDA exchange energy ordering");
    }

    xc_func_end(&func);
    printf("libxc %s API smoke passed\n", version);
    return 0;
}
