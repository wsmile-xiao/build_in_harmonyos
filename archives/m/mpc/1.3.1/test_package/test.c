#include <mpc.h>
#include <mpfr.h>

#include <stdio.h>

int main(void) {
    mpc_t z;
    mpfr_t real;
    mpfr_t imag;
    int rc = 0;

    mpc_init2(z, 128);
    mpfr_init2(real, 128);
    mpfr_init2(imag, 128);

    mpc_set_si_si(z, 1, 2, MPC_RNDNN);
    mpc_sqr(z, z, MPC_RNDNN);
    mpc_real(real, z, MPC_RNDNN);
    mpc_imag(imag, z, MPC_RNDNN);

    if (mpfr_cmp_si(real, -3) != 0 || mpfr_cmp_si(imag, 4) != 0) {
        rc = 1;
    }

    if (rc == 0) {
        puts("MPC complex square API check passed");
    }

    mpfr_clear(imag);
    mpfr_clear(real);
    mpc_clear(z);
    return rc;
}
