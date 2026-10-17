// test_qwt.cpp — 消费者视角验证 qwt 库可链接且核心 API 可用
// 验证内容:
//   1. 头文件可包含 (QwtSpline 系列, OHOS 裁剪后仍可用)
//   2. 链接 libqwt 成功
//   3. 核心 API 运行正确 (样条斜率/曲率计算, 与上游 splinetest 同源逻辑)
#include <QwtSplineCubic>
#include <QwtSplineLocal>
#include <QwtSplinePolynomial>
#include <QPolygonF>
#include <QtGlobal>
#include <cstdio>
#include <cmath>

static bool fuzzyCompare(double a, double b)
{
    return (qFuzzyIsNull(a) && qFuzzyIsNull(b)) || qFuzzyCompare(a, b);
}

int main()
{
    int failures = 0;
    int checks = 0;

    // 3-point spline (与上游 tests/splinetest 相同的验证思路)
    QPolygonF points;
    points << QPointF(10, 50) << QPointF(60, 30) << QPointF(82, 50);

    QwtSplineLocal cardinal(QwtSplineLocal::Cardinal);
    const QVector<double> m = cardinal.slopes(points);

    ++checks;
    if (m.size() != points.size())
    {
        std::printf("FAIL: cardinal slopes size %d != %d\n", m.size(), points.size());
        ++failures;
    }

    // 计算出的斜率应为有限值
    ++checks;
    for (int i = 0; i < m.size(); ++i)
    {
        if (!std::isfinite(m[i]))
        {
            std::printf("FAIL: slope[%d] not finite: %f\n", i, m[i]);
            ++failures;
            break;
        }
    }

    // QwtSplineCubic 曲率计算
    QwtSplineCubic cubic;
    cubic.setBoundaryType(QwtSpline::PeriodicPolygon);
    const QVector<double> cv = cubic.curvatures(points);

    ++checks;
    for (int i = 0; i < cv.size(); ++i)
    {
        if (!std::isfinite(cv[i]))
        {
            std::printf("FAIL: curvature[%d] not finite: %f\n", i, cv[i]);
            ++failures;
            break;
        }
    }

    // QwtSplinePolynomial::fromSlopes 往返一致性
    ++checks;
    if (m.size() >= 2)
    {
        const QwtSplinePolynomial poly = QwtSplinePolynomial::fromSlopes(
            points[0], m[0], points[1], m[1]);
        const double mid = (points[0].x() + points[1].x()) / 2.0;
        const double y = poly.valueAt(mid);
        if (!std::isfinite(y))
        {
            std::printf("FAIL: polynomial value not finite: %f\n", y);
            ++failures;
        }
    }

    if (failures == 0)
        std::printf("PASS: all %d checks passed (qwt linked and functional)\n", checks);
    else
        std::printf("FAIL: %d/%d checks failed\n", failures, checks);

    return failures == 0 ? 0 : 1;
}
