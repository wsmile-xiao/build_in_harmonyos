// test_package — verifies a consumer can compile, link and call the public
// delaunay-triangulation API from installed headers (R34: no shell tests).
// Uses only public members: Delaunay<T>::triangulate(), Triangle<T>::a/b/c
// (const Vector2<T>*), Vector2<T>::x / Vector2<T>::y.
#include <vector>
#include <cassert>
#include <cmath>
#include <iostream>
#include "dt/delaunay.h"

int main()
{
    // Public API: Vector2<double> + Delaunay<double>::triangulate()
    std::vector<Vector2<double>> points;
    points.push_back(Vector2<double>{0.0, 0.0});
    points.push_back(Vector2<double>{1.0, 0.0});
    points.push_back(Vector2<double>{0.0, 1.0});

    Delaunay<double> triangulation;
    const std::vector<Triangle<double>>& triangles = triangulation.triangulate(points);

    assert(triangles.size() == 1 && "3 non-degenerate points must yield exactly 1 triangle");

    // Verify geometry through public members: unit right triangle area == 0.5
    const Triangle<double>& t = triangles[0];
    const double ax = t.a->x, ay = t.a->y;
    const double bx = t.b->x, by = t.b->y;
    const double cx = t.c->x, cy = t.c->y;
    const double area = std::fabs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) / 2.0;

    std::cout << "triangles=" << triangles.size()
              << " area=" << area
              << " (expected 0.5 for unit right triangle)" << std::endl;
    assert(area > 0.49 && area < 0.51 && "unit right triangle area must be 0.5");

    std::cout << "test delaunay-triangulation 2.1: OK (public API callable)" << std::endl;
    return 0;
}
