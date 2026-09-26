/*
 * meschach 1.2b test_package — 消费已安装静态库的真实 API 断言（6 项）。
 * 头文件按本包安装布局取 <meschach/matrix.h>（include/meschach/ 子目录，
 * Debian /usr/include/meschach 同口径）。
 */
#include <math.h>
#include <stdio.h>

#include <meschach/matrix.h>

static int failures = 0;

static void check(int cond, const char *what)
{
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        printf("FAIL - %s\n", what);
        failures++;
    }
}

static int feq(double a, double b)
{
    return fabs(a - b) < 1e-12;
}

int main(void)
{
    MAT *A, *I, *C, *T;
    VEC *x, *y, *z;

    /* 链接面冒烟：version 符号存在且可调用 */
    m_version();

    A = m_get(2, 2);
    I = m_get(2, 2);
    C = m_get(2, 2);
    T = m_get(2, 2);
    x = v_get(2);
    y = v_get(2);
    z = v_get(2);
    check(A && I && C && T && x && y && z, "m_get/v_get 分配 7 个对象");

    /* A = [1 2; 3 4] */
    A->me[0][0] = 1.0;
    A->me[0][1] = 2.0;
    A->me[1][0] = 3.0;
    A->me[1][1] = 4.0;
    check(A->m == 2 && A->n == 2, "矩阵维度保持 m=2 n=2");

    /* C = A*I == A */
    m_ident(I);
    m_mlt(A, I, C);
    check(feq(C->me[0][0], 1.0) && feq(C->me[0][1], 2.0) &&
              feq(C->me[1][0], 3.0) && feq(C->me[1][1], 4.0),
          "m_mlt: A*I == A 四元素一致");

    /* T = A^T，非对角互换 */
    m_transp(A, T);
    check(feq(T->me[0][1], 3.0) && feq(T->me[1][0], 2.0),
          "m_transp: A^T 非对角交换");

    /* y = A*x，x=[1,1]^T → [3,7]^T */
    x->ve[0] = 1.0;
    x->ve[1] = 1.0;
    mv_mlt(A, x, y);
    check(feq(y->ve[0], 3.0) && feq(y->ve[1], 7.0),
          "mv_mlt: A*[1,1]^T == [3,7]^T");

    /* z = x + x == [2,2]^T */
    v_add(x, x, z);
    check(feq(z->ve[0], 2.0) && feq(z->ve[1], 2.0),
          "v_add: x+x == [2,2]^T");

    M_FREE(A);
    M_FREE(I);
    M_FREE(C);
    M_FREE(T);
    V_FREE(x);
    V_FREE(y);
    V_FREE(z);

    printf("meschach test_package: 6 assertions, %d failed\n", failures);
    return failures ? 1 : 0;
}
