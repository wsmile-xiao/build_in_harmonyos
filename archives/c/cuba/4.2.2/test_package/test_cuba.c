#include <stdio.h>
#include <math.h>
#include <cuba.h>

/* 鸿蒙特有消费者测试（R34 反空壳）：真实调用 Cuhre（确定性 cubature）
   积分常数函数 f=1 于 3 维单位立方体 → 精确 1.0。 */

#define NDIM 3
#define NCOMP 1

static int Integrand(const int *ndim, const double xx[],
                     const int *ncomp, double ff[], void *userdata) {
    (void)ndim; (void)xx; (void)ncomp; (void)userdata;
    ff[0] = 1.0;
    return 0;
}

int main(void) {
    double integral[NCOMP], error[NCOMP], prob[NCOMP];
    int nregions, neval, fail;
    char statefile[] = "";

    Cuhre(NDIM, NCOMP, Integrand, NULL, 1,
          1e-8, 1e-12, 0 | 4,  /* LAST | verbosity bits off */
          0, 50000, 9,          /* mineval, maxeval, key */
          statefile, NULL,
          &nregions, &neval, &fail, integral, error, prob);

    if (fail != 0) { printf("FAIL cuhre fail=%d\n", fail); return 1; }
    if (fabs(integral[0] - 1.0) > 1e-9) {
        printf("FAIL integral=%.17g (expect 1)\n", integral[0]);
        return 1;
    }
    printf("PASS test_cuba (Cuhre const-1 integral = %.17g, neval=%d)\n",
           integral[0], neval);
    return 0;
}
