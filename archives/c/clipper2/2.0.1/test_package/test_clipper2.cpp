// test_clipper2.cpp — L1 smoke test for Clipper2 polygon clipping library
// Verifies: area calculation, intersection, union operations
#include "clipper2/clipper.h"
#include <cmath>
#include <iostream>

using namespace Clipper2Lib;

int main() {
    // Test 1: Area calculation — 100x100 square should have area 10000
    Path64 square = MakePath<int>({0, 0, 100, 0, 100, 100, 0, 100});
    double area = std::abs(Area(square));
    if (std::abs(area - 10000.0) > 0.001) {
        std::cerr << "FAIL: area = " << area << ", expected 10000" << std::endl;
        return 1;
    }
    std::cout << "Test 1 PASS: area = " << area << std::endl;

    // Test 2: Intersection — two overlapping 100x100 squares (50x50 overlap)
    Path64 sq1 = MakePath<int>({0, 0, 100, 0, 100, 100, 0, 100});
    Path64 sq2 = MakePath<int>({50, 50, 150, 50, 150, 150, 50, 150});

    Paths64 solution;
    Clipper64 c;
    c.AddSubject({sq1});
    c.AddClip({sq2});
    c.Execute(ClipType::Intersection, FillRule::NonZero, solution);

    double inter_area = std::abs(Area(solution));
    if (std::abs(inter_area - 2500.0) > 0.001) {
        std::cerr << "FAIL: intersection area = " << inter_area << ", expected 2500" << std::endl;
        return 1;
    }
    std::cout << "Test 2 PASS: intersection area = " << inter_area << std::endl;

    // Test 3: Union — two overlapping squares (10000 + 10000 - 2500 = 17500)
    Paths64 union_solution;
    Clipper64 cu;
    cu.AddSubject({sq1});
    cu.AddClip({sq2});
    cu.Execute(ClipType::Union, FillRule::NonZero, union_solution);

    double union_area = std::abs(Area(union_solution));
    if (std::abs(union_area - 17500.0) > 0.001) {
        std::cerr << "FAIL: union area = " << union_area << ", expected 17500" << std::endl;
        return 1;
    }
    std::cout << "Test 3 PASS: union area = " << union_area << std::endl;

    // Test 4: Difference — sq1 minus sq2 (10000 - 2500 = 7500)
    Paths64 diff_solution;
    Clipper64 cd;
    cd.AddSubject({sq1});
    cd.AddClip({sq2});
    cd.Execute(ClipType::Difference, FillRule::NonZero, diff_solution);

    double diff_area = std::abs(Area(diff_solution));
    if (std::abs(diff_area - 7500.0) > 0.001) {
        std::cerr << "FAIL: difference area = " << diff_area << ", expected 7500" << std::endl;
        return 1;
    }
    std::cout << "Test 4 PASS: difference area = " << diff_area << std::endl;

    std::cout << "ALL TESTS PASSED" << std::endl;
    return 0;
}
