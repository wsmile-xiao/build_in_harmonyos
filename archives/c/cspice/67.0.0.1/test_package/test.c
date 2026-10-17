/* CSPICE N0067 —— 真实数值计算验证（非 dlopen 空壳）。
 *
 * 选断言的原则：**不依赖任何内核数据文件**（SPK/LSK 等要另外下载），
 * 但仍是真算，且结果可手工核验：
 *   ① tkvrsn_c("TOOLKIT") 含 "N0067" —— 同时证明装上的是这一版；
 *   ② vnorm_c((3,4,0)) == 5.0（3-4-5 直角三角形，可手算）；
 *   ③ vdot_c(x̂, ŷ) == 0.0（正交，可手算）；
 *   ④ convrt_c 单位换算 1 KM == 1000 METERS（走 CSPICE 的单位表，真查表）；
 *   ⑤ rpd_c() * 180 == π（度/弧度常量自洽）。
 *
 * ②③④ 都是「换个输入结果就变」的真计算，桩实现蒙不过去。
 *
 * 头路径按上游实际布局：<SpiceUsr.h>
 * （函数原型实际在 SpiceZpr.h，由 SpiceUsr.h 间接包含；
 *   生成器占位写的 <cspice.h> 不存在——那是按包名猜的）。
 */
#include <SpiceUsr.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);\
            ++failures;                                                        \
        } else {                                                               \
            printf("[ok] %s\n", (msg));                                        \
        }                                                                      \
    } while (0)

static int near_eq(double a, double b, double eps) { return fabs(a - b) < eps; }

int main(void) {
    const char *ver = tkvrsn_c("TOOLKIT");
    printf("     CSPICE 版本: %s\n", ver ? ver : "(null)");
    CHECK(ver != NULL && strstr(ver, "N0067") != NULL,
          "tkvrsn_c(\"TOOLKIT\") 含 N0067");

    SpiceDouble v345[3] = {3.0, 4.0, 0.0};
    SpiceDouble n = vnorm_c(v345);
    printf("     |(3,4,0)| = %.9f\n", n);
    CHECK(near_eq(n, 5.0, 1e-12), "vnorm_c((3,4,0)) == 5（3-4-5 直角三角形）");

    SpiceDouble ex[3] = {1.0, 0.0, 0.0};
    SpiceDouble ey[3] = {0.0, 1.0, 0.0};
    CHECK(near_eq(vdot_c(ex, ey), 0.0, 1e-15), "vdot_c(x, y) == 0（正交）");

    SpiceDouble meters = 0.0;
    convrt_c(1.0, "KM", "METERS", &meters);
    printf("     1 KM = %.6f METERS\n", meters);
    CHECK(near_eq(meters, 1000.0, 1e-9), "convrt_c 换算 1 KM == 1000 METERS");

    CHECK(near_eq(rpd_c() * 180.0, 3.14159265358979323846, 1e-12),
          "rpd_c() * 180 == pi（度/弧度常量自洽）");

    if (failures) {
        fprintf(stderr, "\ncspice: %d 项断言失败\n", failures);
        return 1;
    }
    printf("\nCSPICE N0067: 全部断言通过\n");
    return 0;
}
