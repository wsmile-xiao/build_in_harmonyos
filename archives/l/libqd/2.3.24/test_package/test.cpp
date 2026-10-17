#include <qd/dd_real.h>
#include <qd/qd_real.h>

#include <cstdlib>
#include <iostream>

int main() {
    const qd_real pi = qd_real::_pi;
    const qd_real root = sqrt(pi);
    const qd_real back = root * root;
    const double err = to_double(fabs(back - pi));
    if (!(err < 1e-28)) {
        std::cerr << "fail pi sqrt roundtrip err=" << err << "\n";
        return 1;
    }

    const dd_real e = dd_real::_e;
    const double ed = to_double(e);
    if (ed < 2.7 || ed > 2.8) {
        std::cerr << "fail dd e=" << ed << "\n";
        return 2;
    }

    const qd_real two(2.0);
    const qd_real four = two * two;
    if (to_double(four) != 4.0) {
        std::cerr << "fail 2*2\n";
        return 3;
    }

    std::cout << "libqd version=2.3.24 pi_sqrt_err=" << err << " e=" << ed << " ok\n";
    return 0;
}
