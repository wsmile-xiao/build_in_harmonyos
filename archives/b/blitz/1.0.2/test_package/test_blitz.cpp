#include <blitz/array.h>

#include <cmath>
#include <iostream>

static int check(bool condition, const char *message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << std::endl;
        return 1;
    }
    std::cout << "PASS: " << message << std::endl;
    return 0;
}

int main() {
    int failures = 0;

    blitz::Array<double, 2> matrix(3, 3);
    blitz::firstIndex i;
    blitz::secondIndex j;
    matrix = i + 2 * j;

    failures += check(matrix(2, 1) == 4.0, "index expression assignment");

    blitz::Array<double, 2> transformed(matrix.shape());
    transformed = matrix * 2.0 + 1.0;

    failures += check(transformed(2, 1) == 9.0, "scalar array expression");
    failures += check(std::fabs(blitz::sum(transformed) - 63.0) < 1e-9, "sum reduction");
    failures += check(transformed.extent(0) == 3 && transformed.extent(1) == 3, "shape preservation");

    if (failures != 0) {
        std::cerr << "blitz 1.0.2 test failed" << std::endl;
        return 1;
    }

    std::cout << "blitz 1.0.2: all 4 assertions passed" << std::endl;
    return 0;
}
