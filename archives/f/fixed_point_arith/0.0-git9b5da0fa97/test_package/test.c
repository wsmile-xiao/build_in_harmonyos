/* test_package 消费者测试 — fixed_point_arith 0.0-git9b5da0fa97
 *
 * 仅通过已安装包的公开头文件与公开 API（f_add/f_neg/f_mul/f_to_df/df_to_f、
 * v_add/v_sub、q_conj/q_rot）验证第三方使用者可编译、链接、调用并得到正确
 * 可观察数值结果。Q1.15：值 = v / 32768。
 */
#include <stdio.h>
#include <stdlib.h>

#include "fixed_point/fixed_point.h"
#include "fixed_point/vector.h"
#include "fixed_point/quaternion.h"

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
    } while (0)

/* Q1.15 固定点运算存在 ±1~2 LSB 舍入误差（FRAC_1_V=32767 非精确 1.0），
 * 旋转结果以容差断言，同时用“旋转两次回到原点”的不变量兜底验证。 */
#define ABS(x) ((x) < 0 ? -(x) : (x))
#define CLOSE(a, b, tol) (ABS((a) - (b)) <= (tol))

int main(void)
{
    /* 1) 标量加减（Q1.15）: 0.5 + 0.25 = 0.75 -> v = 24576 */
    frac a = _frac(16384);   /* 0.5  */
    frac b = _frac(8192);    /* 0.25 */
    frac s = f_add(a, b);
    CHECK(s.v == 24576, "f_add 0.5+0.25 == 0.75");

    /* 2) 取负 */
    frac n = f_neg(a);
    CHECK(n.v == -16384, "f_neg 0.5 == -0.5");

    /* 3) 标量乘法: 0.5 * 0.25 = 0.125 -> v = 4096 */
    frac m = f_mul(a, b);
    CHECK(m.v == 4096, "f_mul 0.5*0.25 == 0.125");

    /* 4) 精度转换: f_to_df(0.5) -> Q2.30 v = 0.5 * 2^30 = 536870912 */
    dfrac d = f_to_df(a);
    CHECK(d.v == 536870912, "f_to_df 0.5 == 536870912 (Q2.30)");
    frac back = df_to_f(d);
    CHECK(back.v == 16384, "df_to_f roundtrip == 0.5");

    /* 5) 向量加/减（逐分量走 f_add/f_sub） */
    vec3 u = {{16384}, {8192}, {0}};    /* (0.5, 0.25, 0)   */
    vec3 w = {{8192},  {16384}, {0}};   /* (0.25, 0.5, 0)   */
    vec3 vs = v_add(u, w);
    CHECK(vs.x.v == 24576 && vs.y.v == 24576, "v_add (0.75, 0.75)");
    vec3 vd = v_sub(u, w);
    CHECK(vd.x.v == 8192 && vd.y.v == -8192, "v_sub (0.25, -0.25)");

    /* 6) 四元数共轭：单位四元数共轭不变 */
    quat q = {{FRAC_1_V}, VEC0};        /* 单位四元数 */
    quat qc = q_conj(q);
    CHECK(qc.r.v == FRAC_1_V && qc.v.x.v == 0 && qc.v.y.v == 0 && qc.v.z.v == 0,
          "q_conj(unit) == unit");

    /* 7) 四元数旋转：绕 z 轴 180 度（q = {0, (0,0,1)}）旋转 (0.5, 0, 0)
     *    -> 反向 (-0.5, 0, 0)，允许固定点舍入 ±2 LSB */
    quat qz = {{0}, {{0}, {0}, {FRAC_1_V}}};
    vec3 v_in = {{16384}, {0}, {0}};
    vec3 v_out = q_rot(qz, v_in);
    CHECK(CLOSE(v_out.x.v, -16384, 2) && v_out.y.v == 0 && v_out.z.v == 0,
          "q_rot 180deg-z (0.5,0,0) -> (-0.5,0,0)");
    /* 不变量：同一旋转连续两次应回到原点 */
    vec3 v_back = q_rot(qz, v_out);
    CHECK(CLOSE(v_back.x.v, 16384, 3) && v_back.y.v == 0 && v_back.z.v == 0,
          "q_rot double-rotation invariant");

    printf("fixed_point_arith consumer test: OK "
           "(scalar/vector/quaternion public API passed)\n");
    return 0;
}
