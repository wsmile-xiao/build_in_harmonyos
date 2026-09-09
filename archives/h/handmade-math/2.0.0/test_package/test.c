#include <stdio.h>

#define HANDMADE_MATH_IMPLEMENTATION
#include <HandmadeMath.h>

int main(void) {
    /* 实质调用被测库 API：向量/矩阵运算并校验结果 */
    HMM_Vec4 v = HMM_V4(1.0f, 2.0f, 3.0f, 4.0f);
    HMM_Vec4 n = HMM_NormV4(v);
    float len = HMM_LenV4(v);
    float dot = HMM_DotV4(v, v);

    HMM_Mat4 m = HMM_M4D(1.0f);
    HMM_Mat4 m2 = HMM_MulM4(m, m);

    if (len < 5.0f || len > 6.0f) {
        printf("FAIL: HMM_LenV4 out of range: %f\n", len);
        return 1;
    }
    if (dot < 29.9f || dot > 30.1f) {
        printf("FAIL: HMM_DotV4 out of range: %f\n", dot);
        return 1;
    }
    if (m2.Elements[0][0] != 1.0f) {
        printf("FAIL: HMM_MulM4 identity broken\n");
        return 1;
    }
    printf("handmade-math 2.0.0: OK (len=%f dot=%f norm=(%f,%f,%f,%f))\n",
           len, dot, n.X, n.Y, n.Z, n.W);
    return 0;
}
