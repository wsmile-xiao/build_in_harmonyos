#include <Imath/ImathBox.h>
#include <Imath/ImathMatrix.h>
#include <Imath/ImathVec.h>

#include <cmath>
#include <iostream>

int main()
{
    Imath::V3f value(1.0F, 2.0F, 3.0F);
    Imath::M44f transform;
    transform.makeIdentity();
    transform.translate(Imath::V3f(4.0F, -2.0F, 1.0F));
    const Imath::V3f result = value * transform;
    if (std::fabs(result.x - 5.0F) > 1e-6F ||
        std::fabs(result.y) > 1e-6F ||
        std::fabs(result.z - 4.0F) > 1e-6F) {
        std::cerr << "unexpected transformed vector\n";
        return 1;
    }
    const Imath::Box3f empty_box;
    if (!empty_box.isEmpty()) {
        std::cerr << "default box was unexpectedly valid\n";
        return 2;
    }
    std::cout << "imath transform and empty-box failure-path checks passed\n";
    return 0;
}
