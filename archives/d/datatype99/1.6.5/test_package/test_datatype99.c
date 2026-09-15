#include <stdio.h>
#include <assert.h>
#include <datatype99.h>

/* 鸿蒙特有消费者测试（R34 反空壳）：真实使用 datatype() 宏建模+模式匹配。 */

datatype(
    Shape,
    (Point),
    (Circle, double),
    (Rect, double, double)
);

static double area(Shape s) {
    match(s) {
        of(Point) return 0.0;
        of(Circle, r) return 3.14159265358979 * (*r) * (*r);
        of(Rect, w, h) return (*w) * (*h);
    }
    return -1.0;
}

int main(void) {
    Shape p = Point();
    Shape c = Circle(1.0);
    Shape r = Rect(2.0, 3.0);

    double ap = area(p), ac = area(c), ar = area(r);
    if (ap != 0.0) { printf("FAIL point area %g\n", ap); return 1; }
    if (ac < 3.1415 || ac > 3.1416) { printf("FAIL circle area %g\n", ac); return 1; }
    if (ar != 6.0) { printf("FAIL rect area %g\n", ar); return 1; }

    printf("PASS test_datatype99 (point/circle/rect match ok)\n");
    return 0;
}
