#include <cmath>
#include <iostream>
#include <stdexcept>
#include "sopt/conjugate_gradient.h"
#include "sopt/logging.h"
#include "sopt/utilities.h"
#include "sopt/wavelets.h"

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    using Vector = sopt::Vector<double>;
    using Matrix = sopt::Matrix<double>;
    Matrix a(2, 2);
    a << 4, 1, 1, 3;
    Vector b(2);
    b << 1, 2;
    auto result = sopt::ConjugateGradient(100, 1e-12)(a, b);
    require(result.good && (a * result.result - b).norm() < 1e-10,
            "conjugate gradient residual");
    std::cout << "PASS conjugate-gradient\n";

    sopt::Array<double> input(16);
    for (int i = 0; i < 16; ++i) input(i) = std::sin(i * 0.3);
    auto wavelet = sopt::wavelets::factory("DB2", 2);
    auto coefficients = wavelet.direct(input);
    auto restored = wavelet.indirect(coefficients);
    require(input.isApprox(restored, 1e-10), "wavelet round trip");
    std::cout << "PASS wavelet-round-trip\n";

    sopt::Image<> image(2, 2);
    image << 0, 0.25, 0.5, 1;
    sopt::utilities::write_tiff(image, "sopt-consumer.tiff");
    auto loaded = sopt::utilities::read_tiff("sopt-consumer.tiff");
    require(loaded.rows() == 2 && loaded.cols() == 2
            && (loaded - image).abs().maxCoeff() < 0.005, "TIFF round trip");
    std::cout << "PASS TIFF-round-trip\n";

    sopt::logging::Log::setLevel("consumer", sopt::logging::Log::error);
    require(sopt::logging::Log::getLog("consumer").getLevel()
            == sopt::logging::Log::error, "compiled logger state");
    std::cout << "PASS logger-state\nSOPT_CONSUMER_PASS 4/4\n";
}
