#include <cassert>
#include <iostream>
#include "CglParam.hpp"

int main() {
    CglParam params;
    assert(params.getEPS() > 0.0);
    assert(params.getEPS_COEFF() > 0.0);
    params.setEPS(1e-7);
    assert(params.getEPS() == 1e-7);
    std::cout << "Cgl 0.60.10 parameter API: PASS\n";
    return 0;
}
