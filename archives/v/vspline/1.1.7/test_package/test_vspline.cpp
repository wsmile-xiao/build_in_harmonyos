// vspline test_package: exercise the header-only b-spline API.
// Mirrors the upstream quickstart example: prefilter a 2D float array,
// evaluate the spline at a coordinate, and verify remap/transform round-trip.
#include <vspline/vspline.h>

#include <cassert>
#include <iostream>

int main()
{
    // a 2D vigra::MultiArray of data
    vigra::MultiArray<2, float> a(10, 20);
    a = 42;

    using spline_type = vspline::bspline<float, 2>;
    spline_type bspl(a.shape());

    bspl.core = a;
    bspl.prefilter();

    using coordinate_type = vigra::TinyVector<float, 2>;
    using eval_type = vspline::evaluator<coordinate_type, float>;
    eval_type ev(bspl);

    float x = 3, y = 4;
    coordinate_type coordinate(x, y);
    float result;
    ev.eval(coordinate, result);

    auto r = ev(coordinate);
    assert(r == result);

    // remap an array of coordinates through the spline
    vigra::MultiArray<1, coordinate_type> coordinate_array(3);
    coordinate_array[0] = coordinate_array[1] = coordinate_array[2] = coordinate;
    vigra::MultiArray<1, float> target_array(3);
    vspline::remap(a, coordinate_array, target_array);

    auto ic = coordinate_array.begin();
    for (auto k : target_array)
        assert(k == ev(*(ic++)));

    // constant data interpolated at any coordinate must return 42
    if (result != 42.0f)
    {
        std::cerr << "unexpected evaluation result: " << result << std::endl;
        return 1;
    }

    std::cout << "vspline 1.1.7 test passed: eval(coordinate) == 42" << std::endl;
    return 0;
}
