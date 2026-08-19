#include <ql/quantlib.hpp>

#include <cmath>
#include <iostream>

int main() {
    using namespace QuantLib;

    const Date today(15, May, 2026);
    Settings::instance().evaluationDate() = today;
    const Handle<YieldTermStructure> curve(
        ext::make_shared<FlatForward>(today, 0.05, Actual365Fixed()));
    const DiscountFactor discount = curve->discount(today + Period(1, Years));

    if (!(discount > 0.0 && discount < 1.0) ||
        std::abs(discount - std::exp(-0.05)) > 1.0e-10) {
        return 1;
    }

    std::cout << "quantlib curve test passed: " << discount << '\n';
    return 0;
}
