#include <CLHEP/Vector/ThreeVector.h>

#include <cmath>
#include <iostream>

int main() {
    const CLHEP::Hep3Vector x_axis(1.0, 0.0, 0.0);
    const CLHEP::Hep3Vector y_axis(0.0, 1.0, 0.0);
    const CLHEP::Hep3Vector z_axis = x_axis.cross(y_axis);

    if (std::abs(z_axis.z() - 1.0) > 1e-12 ||
        std::abs(z_axis.mag() - 1.0) > 1e-12) {
        std::cerr << "CLHEP Hep3Vector cross-product assertion failed\n";
        return 1;
    }

    return 0;
}
