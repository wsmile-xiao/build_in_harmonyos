#include <libasd/libasd.hpp>

int main() {
    const auto bipolar = asd::to_voltage<float>(asd::AD_range::bipolar_2_5V);
    const auto unipolar = asd::to_voltage<double>(asd::AD_range::unipolar_5_0V);
    if (bipolar.first != -2.5f || bipolar.second != 2.5f) return 1;
    if (unipolar.first != 0.0 || unipolar.second != 5.0) return 2;
    return 0;
}
