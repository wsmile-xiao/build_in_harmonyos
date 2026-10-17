/* test_package for mpfit: two real fits against libmpfit.
 * Case 1 (linear): y = a - b*x, 10 points, checks status 1..8 and params.
 * Case 2 (quadratic): y = a + b*x + c*x^2 with one fixed param.
 * Both must print PASS lines; main fails if any case fails.
 */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "mpfit.h"

struct vars_struct {
    double *x;
    double *y;
    double *ey;
};

static int linfunc(int m, int n, double *p, double *dy, double **dvec, void *vars)
{
    struct vars_struct *v = (struct vars_struct *)vars;
    int i;
    (void)dvec;
    for (i = 0; i < m; i++)
        dy[i] = (v->y[i] - p[0] - p[1] * v->x[i]) / v->ey[i];
    return 0;
}

static int quadfunc(int m, int n, double *p, double *dy, double **dvec, void *vars)
{
    struct vars_struct *v = (struct vars_struct *)vars;
    int i;
    (void)dvec;
    for (i = 0; i < m; i++)
        dy[i] = (v->y[i] - p[0] - p[1] * v->x[i] - p[2] * v->x[i] * v->x[i]) / v->ey[i];
    return 0;
}

static int test_linear(void)
{
    double x[] = {-1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0};
    double y[10];
    double ey[10];
    double p[2] = {0.0, 0.0};
    double perror[2];
    mp_par pars[2];
    struct vars_struct v;
    mp_result result;
    int i, status;
    for (i = 0; i < 10; i++) {
        y[i] = 3.2 - 1.78 * x[i];
        ey[i] = 0.5;
    }
    memset(&result, 0, sizeof(result));
    result.xerror = perror;
    memset(pars, 0, sizeof(pars));
    v.x = x; v.y = y; v.ey = ey;
    status = mpfit(linfunc, 10, 2, p, pars, 0, (void *)&v, &result);
    printf("case linear: status=%d bestnorm=%f p0=%f p1=%f\n",
           status, result.bestnorm, p[0], p[1]);
    if (status < 1 || status > 8) {
        printf("case linear: FAIL (bad status)\n");
        return 1;
    }
    if (fabs(p[0] - 3.2) > 0.2 || fabs(p[1] + 1.78) > 0.2) {
        printf("case linear: FAIL (params off)\n");
        return 1;
    }
    printf("case linear: PASS\n");
    return 0;
}

static int test_quad(void)
{
    double x[] = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0};
    double y[10];
    double ey[10];
    double p[3] = {1.0, 0.0, 0.0};
    double perror[3];
    mp_par pars[3];
    struct vars_struct v;
    mp_result result;
    int i, status;
    for (i = 0; i < 10; i++) {
        y[i] = 4.7 + 0.0 * x[i] + 6.2 * x[i] * x[i];
        ey[i] = 0.5;
    }
    memset(&result, 0, sizeof(result));
    result.xerror = perror;
    memset(pars, 0, sizeof(pars));
    pars[1].fixed = 1; /* fix linear term, fit the other two */
    v.x = x; v.y = y; v.ey = ey;
    status = mpfit(quadfunc, 10, 3, p, pars, 0, (void *)&v, &result);
    printf("case quad: status=%d bestnorm=%f p0=%f p1=%f p2=%f\n",
           status, result.bestnorm, p[0], p[1], p[2]);
    if (status < 1 || status > 8) {
        printf("case quad: FAIL (bad status)\n");
        return 1;
    }
    if (fabs(p[0] - 4.7) > 0.5 || fabs(p[2] - 6.2) > 0.5) {
        printf("case quad: FAIL (params off)\n");
        return 1;
    }
    printf("case quad: PASS\n");
    return 0;
}

int main(void)
{
    int rc = 0;
    rc |= test_linear();
    rc |= test_quad();
    if (rc == 0)
        printf("test_mpfit: ALL PASS (2/2 cases)\n");
    else
        printf("test_mpfit: FAILURES present\n");
    return rc;
}
