#include <geogram/basic/common.h>
#include <geogram/basic/geometry.h>

#include <cmath>

int main() {
    GEO::initialize(GEO::GEOGRAM_INSTALL_NONE);
    GEO::vec3 a(1.0, 2.0, 3.0);
    GEO::vec3 b(2.0, 4.0, 6.0);
    GEO::vec3 c = b - a;
    if (std::fabs(c[0] - 1.0) > 1e-12 ||
        std::fabs(c[1] - 2.0) > 1e-12 ||
        std::fabs(c[2] - 3.0) > 1e-12) {
        return 1;
    }
    return 0;
}

