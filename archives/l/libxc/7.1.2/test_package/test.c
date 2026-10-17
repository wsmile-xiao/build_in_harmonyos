#include <math.h>
#include <stdio.h>

#include <xc.h>
#include <xc_funcs.h>

int main(void)
{
    int major = 0;
    int minor = 0;
    int micro = 0;
    xc_func_type functional;
    const xc_func_info_type *info;
    const double rho = 0.5;
    double zk = 0.0;
    double vrho = 0.0;
    double v2rho2 = 0.0;
    double v3rho3 = 0.0;
    const double cx = 0.75 * pow(3.0 / acos(-1.0), 1.0 / 3.0);
    const double expected = -cx * pow(rho, 1.0 / 3.0);

    xc_version(&major, &minor, &micro);
    if (major != 7 || minor != 1 || micro != 2) {
        return 10;
    }
    if (xc_func_init(&functional, XC_LDA_X, XC_UNPOLARIZED) != 0) {
        return 11;
    }
    info = xc_func_get_info(&functional);
    if ((xc_func_info_get_flags(info) & XC_FLAGS_HAVE_KXC) == 0) {
        xc_func_end(&functional);
        return 12;
    }
    if ((xc_func_info_get_flags(info) & XC_FLAGS_HAVE_LXC) != 0) {
        xc_func_end(&functional);
        return 15;
    }
    xc_lda_exc_vxc_fxc_kxc(
        &functional, 1, &rho, &zk, &vrho, &v2rho2, &v3rho3
    );
    xc_func_end(&functional);
    if (!isfinite(zk) || !isfinite(vrho) || !isfinite(v2rho2) ||
        !isfinite(v3rho3)) {
        return 13;
    }
    if (fabs(zk - expected) > 1.0e-11) {
        return 14;
    }
    printf("Libxc 7.1.2 C KXC consumer: PASS\n");
    return 0;
}
