#include <stdint.h>
#include <stdio.h>
#include <math.h>

#include <libocas.h>
#include <libqp.h>

static double Hcol0[2] = {1.0, 0.0};
static double Hcol1[2] = {0.0, 1.0};

static const double *get_col(uint32_t i)
{
    return (i == 0) ? Hcol0 : Hcol1;
}

int main(void)
{
    int failed = 0;

    /* CHECK 1: column-major index macro from the public header. */
    if (LIBOCAS_INDEX(1, 2, 10) != 21) {
        printf("FAIL: LIBOCAS_INDEX(1,2,10) != 21\n");
        failed++;
    } else {
        printf("CHECK-OK: LIBOCAS_INDEX\n");
    }

    /* CHECK 2..6: real QP solver call on a 2-variable simplex problem:
       min 0.5*(x0^2+x1^2) s.t. x0+x1 == 1, x >= 0.
       Optimum is x = [0.5, 0.5] with QP = 0.25. */
    {
        double diag_H[2] = {1.0, 1.0};
        double f[2] = {0.0, 0.0};
        double b[1] = {1.0};
        uint32_t I[2] = {1, 1};
        uint8_t S[1] = {0};
        double x[2] = {0.5, 0.5};
        libqp_state_T st = libqp_splx_solver(get_col, diag_H, f, b, I, S, x, 2,
                                             1000, 1e-9, 1e-9, -1e15, NULL);
        if (st.exitflag < 0 || st.exitflag == 100) {
            printf("FAIL: libqp_splx_solver exitflag=%d\n", (int)st.exitflag);
            failed++;
        } else {
            printf("CHECK-OK: libqp_splx_solver exitflag=%d nIter=%u\n",
                   (int)st.exitflag, (unsigned)st.nIter);
        }
        if (!(st.QP < 1e29 && st.QD > -1e29)) {
            printf("FAIL: QP/QD not finite QP=%f QD=%f\n", st.QP, st.QD);
            failed++;
        } else {
            printf("CHECK-OK: QP=%f QD=%f finite\n", st.QP, st.QD);
        }
        if (fabs((x[0] + x[1]) - 1.0) > 1e-4) {
            printf("FAIL: simplex sum x0+x1=%f != 1\n", x[0] + x[1]);
            failed++;
        } else {
            printf("CHECK-OK: simplex sum=%f\n", x[0] + x[1]);
        }
        if (x[0] < -1e-6 || x[1] < -1e-6) {
            printf("FAIL: x negative x0=%f x1=%f\n", x[0], x[1]);
            failed++;
        } else {
            printf("CHECK-OK: x=[%f,%f] non-negative\n", x[0], x[1]);
        }
        if (st.nIter > 1000) {
            printf("FAIL: nIter %u exceeds budget\n", (unsigned)st.nIter);
            failed++;
        } else {
            printf("CHECK-OK: nIter=%u within budget\n", (unsigned)st.nIter);
        }
    }

    if (failed != 0) {
        printf("RESULT: %d check(s) failed\n", failed);
        return 1;
    }
    printf("RESULT: all 6 checks passed\n");
    return 0;
}
