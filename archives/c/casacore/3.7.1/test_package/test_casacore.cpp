// Test casacore basic functionality - Vector and Array operations
// This test creates a Vector, assigns values, and verifies basic operations.

#include <casacore/casa/Arrays/Vector.h>
#include <casacore/casa/Arrays/Array.h>
#include <casacore/casa/Arrays/IPosition.h>
#include <casacore/casa/iostream.h>

#include <cstdlib>

int main() {
    // Test 1: Create a vector of size 5 and assign a value
    casacore::Vector<int> v(5);
    v = 42;
    if (v[0] != 42 || v[4] != 42) {
        return 1;
    }

    // Test 2: Create a 2D array
    casacore::IPosition shape(2, 3, 4);
    casacore::Array<double> arr(shape);
    arr = 3.14;
    if (arr(casacore::IPosition(2, 0, 0)) != 3.14) {
        return 2;
    }

    // Test 3: Vector arithmetic
    casacore::Vector<double> a(3), b(3);
    a = 1.0;
    b = 2.0;
    casacore::Vector<double> c = a + b;
    if (c[0] != 3.0) {
        return 3;
    }

    // Test 4: Vector size
    if (v.size() != 5) {
        return 4;
    }

    return 0;
}
