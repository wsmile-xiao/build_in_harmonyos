/* test_udunits — 实质调用 udunits2 库 API（R34：禁止空壳测试）。
 * 覆盖：XML 数据库加载、单位查找、转换器创建、数值转换断言、
 *       反向转换、温度换算、不兼容单位拒绝。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <udunits2.h>

static int failures = 0;

#define CHECK(cond)                                                       \
    do {                                                                  \
        if (!(cond)) {                                                    \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            failures++;                                                   \
        }                                                                 \
    } while (0)

static void near_eq(double got, double want, double eps, const char *what) {
    if (fabs(got - want) > eps) {
        fprintf(stderr, "FAIL %s: got %.6f want %.6f\n", what, got, want);
        failures++;
    }
}

int main(void) {
    /* 1. 加载 XML 单位数据库（UDUNITS2_XML_PATH 由 test_package 环境注入） */
    ut_system *sys = ut_read_xml(NULL);
    CHECK(sys != NULL);
    if (!sys) {
        fprintf(stderr, "ut_read_xml failed (status=%d)\n", ut_get_status());
        return 1;
    }

    /* 2. 单位查找：meter / foot / hour / degree_Celsius */
    ut_unit *meter = ut_get_unit_by_name(sys, "meter");
    ut_unit *foot = ut_get_unit_by_name(sys, "foot");
    ut_unit *hour = ut_get_unit_by_name(sys, "hour");
    ut_unit *second = ut_get_unit_by_name(sys, "second");
    ut_unit *kelvin = ut_get_unit_by_name(sys, "kelvin");
    ut_unit *celsius = ut_get_unit_by_name(sys, "degree_Celsius");
    CHECK(meter != NULL);
    CHECK(foot != NULL);
    CHECK(hour != NULL);
    CHECK(second != NULL);
    CHECK(kelvin != NULL);
    CHECK(celsius != NULL);

    /* 3. 转换器创建：m -> ft */
    cv_converter *m2ft = ut_get_converter(meter, foot);
    CHECK(m2ft != NULL);

    /* 4. 数值转换断言：1 m = 3.28084 ft */
    near_eq(cv_convert_double(m2ft, 1.0), 3.28084, 1e-3, "1 m -> ft");
    near_eq(cv_convert_double(m2ft, 1000.0), 3280.84, 1e-2, "1000 m -> ft");

    /* 5. 反向转换：ft -> m */
    cv_converter *ft2m = ut_get_converter(foot, meter);
    CHECK(ft2m != NULL);
    near_eq(cv_convert_double(ft2m, 3.28084), 1.0, 1e-4, "3.28084 ft -> m");

    /* 6. 时间转换：1 h = 3600 s */
    cv_converter *h2s = ut_get_converter(hour, second);
    CHECK(h2s != NULL);
    near_eq(cv_convert_double(h2s, 1.0), 3600.0, 1e-6, "1 h -> s");

    /* 7. 温度换算：273.15 K = 0 degC，373.15 K = 100 degC */
    cv_converter *k2c = ut_get_converter(kelvin, celsius);
    CHECK(k2c != NULL);
    near_eq(cv_convert_double(k2c, 273.15), 0.0, 1e-3, "273.15 K -> degC");
    near_eq(cv_convert_double(k2c, 373.15), 100.0, 1e-3, "373.15 K -> degC");

    /* 8. 不兼容单位拒绝：hour -> meter 应返回 NULL */
    cv_converter *bad = ut_get_converter(hour, meter);
    CHECK(bad == NULL);

    /* 9. ut_are_convertible 一致性检查 */
    CHECK(ut_are_convertible(meter, foot) == 1);
    CHECK(ut_are_convertible(hour, meter) == 0);

    /* 清理 */
    if (m2ft) cv_free(m2ft);
    if (ft2m) cv_free(ft2m);
    if (h2s) cv_free(h2s);
    if (k2c) cv_free(k2c);
    if (meter) ut_free(meter);
    if (foot) ut_free(foot);
    if (hour) ut_free(hour);
    if (second) ut_free(second);
    if (kelvin) ut_free(kelvin);
    if (celsius) ut_free(celsius);
    ut_free_system(sys);

    if (failures > 0) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test_udunits: all assertions passed\n");
    return 0;
}
