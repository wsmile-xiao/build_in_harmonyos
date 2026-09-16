#include <stdio.h>
#include <math.h>
#include <cqrlib.h>

/* 鸿蒙特有消费者测试（R34 反空壳）：真实调用静态库导出 API。
   单位四元数 q=(1,0,0,0)：范数=1；q*q=q；轴角 (0,0,1) 转 90° 四元数后
   旋转向量 (1,0,0) 应得 (0,1,0)。 */
int main(void) {
    CQRQuaternionHandle q1 = NULL, q2 = NULL, q3 = NULL;
    double norm = 0.0, w = 0.0, x = 0.0, y = 0.0, z = 0.0;
    double axis[3] = {0.0, 0.0, 1.0};
    double v[3] = {1.0, 0.0, 0.0};
    double pi = 3.14159265358979323846;

    if (CQRCreateQuaternion(&q1, 1.0, 0.0, 0.0, 0.0) != 0) { printf("FAIL create q1\n"); return 1; }
    if (CQRNorm(&norm, q1) != 0 || fabs(norm - 1.0) > 1e-12) { printf("FAIL norm %.17g\n", norm); return 1; }

    if (CQRCreateQuaternion(&q2, 1.0, 0.0, 0.0, 0.0) != 0) { printf("FAIL create q2\n"); return 1; }
    if (CQRCreateEmptyQuaternion(&q3) != 0) { printf("FAIL create q3\n"); return 1; }
    if (CQRMultiply(q3, q1, q2) != 0) { printf("FAIL multiply\n"); return 1; }
    if (CQRGetQuaternionW(&w, q3) || CQRGetQuaternionX(&x, q3) ||
        CQRGetQuaternionY(&y, q3) || CQRGetQuaternionZ(&z, q3)) { printf("FAIL get\n"); return 1; }
    if (fabs(w - 1.0) > 1e-12 || fabs(x) > 1e-12 || fabs(y) > 1e-12 || fabs(z) > 1e-12) {
        printf("FAIL identity mul got [%g,%g,%g,%g]\n", w, x, y, z); return 1;
    }

    /* 绕 z 轴 90° 旋转 (1,0,0) → (0,1,0)。
       CQRRotateByQuaternion(out, q, in)：out 为输出向量（写 w[0..2]），
       in 为输入向量，不做原地旋转。 */
    {
        double out[3] = {0.0, 0.0, 0.0};
        if (CQRAxis2Quaternion(q1, axis, pi / 2.0) != 0) { printf("FAIL axis2quat\n"); return 1; }
        if (CQRRotateByQuaternion(out, q1, v) != 0) { printf("FAIL rotate\n"); return 1; }
        if (fabs(out[0]) > 1e-12 || fabs(out[1] - 1.0) > 1e-12 || fabs(out[2]) > 1e-12) {
            printf("FAIL rotate got [%g,%g,%g]\n", out[0], out[1], out[2]); return 1;
        }
    }

    CQRFreeQuaternion(&q1);
    CQRFreeQuaternion(&q2);
    CQRFreeQuaternion(&q3);
    printf("PASS test_cqrlib (norm=1, identity-mul, z90 rotate ok)\n");
    return 0;
}
