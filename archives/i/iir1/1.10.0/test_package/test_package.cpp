#include <Iir.h>

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

constexpr double kSampleRate = 48000.0;
constexpr double kCutoff = 2000.0;
constexpr double kCenter = 4000.0;
constexpr double kWidth = 1000.0;
constexpr double kGainDb = 6.0;
constexpr double kRippleDb = 1.0;
constexpr double kStopBandDb = 40.0;

template <typename Filter>
int impulse_response_case(Filter& filter)
{
    double magnitude = 0.0;
    for (int i = 0; i < 64; ++i) {
        const double output = filter.filter(i == 0 ? 1.0 : 0.0);
        if (!std::isfinite(output)) {
            return 1;
        }
        magnitude += std::abs(output);
    }
    return magnitude > 1e-12 ? 0 : 1;
}

template <int Order>
int butterworth_lowpass()
{
    Iir::Butterworth::LowPass<Order> filter;
    filter.setup(kSampleRate, kCutoff);
    return impulse_response_case(filter);
}

template <int Order>
int butterworth_highpass()
{
    Iir::Butterworth::HighPass<Order> filter;
    filter.setup(kSampleRate, kCutoff);
    return impulse_response_case(filter);
}

template <int Order>
int butterworth_bandpass()
{
    Iir::Butterworth::BandPass<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth);
    return impulse_response_case(filter);
}

template <int Order>
int butterworth_bandstop()
{
    Iir::Butterworth::BandStop<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth);
    return impulse_response_case(filter);
}

template <int Order>
int butterworth_lowshelf()
{
    Iir::Butterworth::LowShelf<Order> filter;
    filter.setup(kSampleRate, kCutoff, kGainDb);
    return impulse_response_case(filter);
}

template <int Order>
int butterworth_highshelf()
{
    Iir::Butterworth::HighShelf<Order> filter;
    filter.setup(kSampleRate, kCutoff, kGainDb);
    return impulse_response_case(filter);
}

template <int Order>
int butterworth_bandshelf()
{
    Iir::Butterworth::BandShelf<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth, kGainDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev1_lowpass()
{
    Iir::ChebyshevI::LowPass<Order> filter;
    filter.setup(kSampleRate, kCutoff, kRippleDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev1_highpass()
{
    Iir::ChebyshevI::HighPass<Order> filter;
    filter.setup(kSampleRate, kCutoff, kRippleDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev1_bandpass()
{
    Iir::ChebyshevI::BandPass<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth, kRippleDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev1_bandstop()
{
    Iir::ChebyshevI::BandStop<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth, kRippleDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev1_lowshelf()
{
    Iir::ChebyshevI::LowShelf<Order> filter;
    filter.setup(kSampleRate, kCutoff, kGainDb, kRippleDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev1_highshelf()
{
    Iir::ChebyshevI::HighShelf<Order> filter;
    filter.setup(kSampleRate, kCutoff, kGainDb, kRippleDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev1_bandshelf()
{
    Iir::ChebyshevI::BandShelf<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth, kGainDb, kRippleDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev2_lowpass()
{
    Iir::ChebyshevII::LowPass<Order> filter;
    filter.setup(kSampleRate, kCutoff, kStopBandDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev2_highpass()
{
    Iir::ChebyshevII::HighPass<Order> filter;
    filter.setup(kSampleRate, kCutoff, kStopBandDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev2_bandpass()
{
    Iir::ChebyshevII::BandPass<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth, kStopBandDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev2_bandstop()
{
    Iir::ChebyshevII::BandStop<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth, kStopBandDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev2_lowshelf()
{
    Iir::ChebyshevII::LowShelf<Order> filter;
    filter.setup(kSampleRate, kCutoff, kGainDb, kStopBandDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev2_highshelf()
{
    Iir::ChebyshevII::HighShelf<Order> filter;
    filter.setup(kSampleRate, kCutoff, kGainDb, kStopBandDb);
    return impulse_response_case(filter);
}

template <int Order>
int chebyshev2_bandshelf()
{
    Iir::ChebyshevII::BandShelf<Order> filter;
    filter.setup(kSampleRate, kCenter, kWidth, kGainDb, kStopBandDb);
    return impulse_response_case(filter);
}

int rbj_lowpass()
{
    Iir::RBJ::LowPass filter;
    filter.setup(kSampleRate, kCutoff);
    return impulse_response_case(filter);
}

int rbj_highpass()
{
    Iir::RBJ::HighPass filter;
    filter.setup(kSampleRate, kCutoff);
    return impulse_response_case(filter);
}

int rbj_bandpass1()
{
    Iir::RBJ::BandPass1 filter;
    filter.setup(kSampleRate, kCenter, 1.0);
    return impulse_response_case(filter);
}

int rbj_bandpass2()
{
    Iir::RBJ::BandPass2 filter;
    filter.setup(kSampleRate, kCenter, 1.0);
    return impulse_response_case(filter);
}

int rbj_bandstop()
{
    Iir::RBJ::BandStop filter;
    filter.setup(kSampleRate, kCenter, 1.0);
    return impulse_response_case(filter);
}

int rbj_notch()
{
    Iir::RBJ::IIRNotch filter;
    filter.setup(kSampleRate, kCenter, 10.0);
    return impulse_response_case(filter);
}

int rbj_lowshelf()
{
    Iir::RBJ::LowShelf filter;
    filter.setup(kSampleRate, kCutoff, kGainDb);
    return impulse_response_case(filter);
}

int rbj_highshelf()
{
    Iir::RBJ::HighShelf filter;
    filter.setup(kSampleRate, kCutoff, kGainDb);
    return impulse_response_case(filter);
}

int rbj_bandshelf()
{
    Iir::RBJ::BandShelf filter;
    filter.setup(kSampleRate, kCenter, kGainDb, 1.0);
    return impulse_response_case(filter);
}

int rbj_allpass()
{
    Iir::RBJ::AllPass filter;
    filter.setup(kSampleRate, kCenter);
    return impulse_response_case(filter);
}

int invalid_parameter_case()
{
    try {
        Iir::Butterworth::LowPass<3> filter;
        filter.setup(kSampleRate, kSampleRate / 2.0);
    } catch (const std::invalid_argument&) {
        return 0;
    }
    return 1;
}

int dispatch(const std::string& name)
{
#define HANDLE_CASE(case_name, expression) \
    if (name == case_name) {                \
        return expression;                  \
    }

    HANDLE_CASE("butterworth-lowpass-2", butterworth_lowpass<2>())
    HANDLE_CASE("butterworth-lowpass-4", butterworth_lowpass<4>())
    HANDLE_CASE("butterworth-highpass-2", butterworth_highpass<2>())
    HANDLE_CASE("butterworth-highpass-4", butterworth_highpass<4>())
    HANDLE_CASE("butterworth-bandpass-2", butterworth_bandpass<2>())
    HANDLE_CASE("butterworth-bandpass-4", butterworth_bandpass<4>())
    HANDLE_CASE("butterworth-bandstop-2", butterworth_bandstop<2>())
    HANDLE_CASE("butterworth-bandstop-4", butterworth_bandstop<4>())
    HANDLE_CASE("butterworth-lowshelf-2", butterworth_lowshelf<2>())
    HANDLE_CASE("butterworth-lowshelf-4", butterworth_lowshelf<4>())
    HANDLE_CASE("butterworth-highshelf-2", butterworth_highshelf<2>())
    HANDLE_CASE("butterworth-highshelf-4", butterworth_highshelf<4>())
    HANDLE_CASE("butterworth-bandshelf-2", butterworth_bandshelf<2>())
    HANDLE_CASE("butterworth-bandshelf-4", butterworth_bandshelf<4>())

    HANDLE_CASE("chebyshev1-lowpass-2", chebyshev1_lowpass<2>())
    HANDLE_CASE("chebyshev1-lowpass-4", chebyshev1_lowpass<4>())
    HANDLE_CASE("chebyshev1-highpass-2", chebyshev1_highpass<2>())
    HANDLE_CASE("chebyshev1-highpass-4", chebyshev1_highpass<4>())
    HANDLE_CASE("chebyshev1-bandpass-2", chebyshev1_bandpass<2>())
    HANDLE_CASE("chebyshev1-bandpass-4", chebyshev1_bandpass<4>())
    HANDLE_CASE("chebyshev1-bandstop-2", chebyshev1_bandstop<2>())
    HANDLE_CASE("chebyshev1-bandstop-4", chebyshev1_bandstop<4>())
    HANDLE_CASE("chebyshev1-lowshelf-2", chebyshev1_lowshelf<2>())
    HANDLE_CASE("chebyshev1-lowshelf-4", chebyshev1_lowshelf<4>())
    HANDLE_CASE("chebyshev1-highshelf-2", chebyshev1_highshelf<2>())
    HANDLE_CASE("chebyshev1-highshelf-4", chebyshev1_highshelf<4>())
    HANDLE_CASE("chebyshev1-bandshelf-2", chebyshev1_bandshelf<2>())
    HANDLE_CASE("chebyshev1-bandshelf-4", chebyshev1_bandshelf<4>())

    HANDLE_CASE("chebyshev2-lowpass-2", chebyshev2_lowpass<2>())
    HANDLE_CASE("chebyshev2-highpass-2", chebyshev2_highpass<2>())
    HANDLE_CASE("chebyshev2-bandpass-2", chebyshev2_bandpass<2>())
    HANDLE_CASE("chebyshev2-bandstop-2", chebyshev2_bandstop<2>())
    HANDLE_CASE("chebyshev2-lowshelf-2", chebyshev2_lowshelf<2>())
    HANDLE_CASE("chebyshev2-highshelf-2", chebyshev2_highshelf<2>())
    HANDLE_CASE("chebyshev2-bandshelf-2", chebyshev2_bandshelf<2>())

    HANDLE_CASE("rbj-lowpass", rbj_lowpass())
    HANDLE_CASE("rbj-highpass", rbj_highpass())
    HANDLE_CASE("rbj-bandpass1", rbj_bandpass1())
    HANDLE_CASE("rbj-bandpass2", rbj_bandpass2())
    HANDLE_CASE("rbj-bandstop", rbj_bandstop())
    HANDLE_CASE("rbj-notch", rbj_notch())
    HANDLE_CASE("rbj-lowshelf", rbj_lowshelf())
    HANDLE_CASE("rbj-highshelf", rbj_highshelf())
    HANDLE_CASE("rbj-bandshelf", rbj_bandshelf())
    HANDLE_CASE("rbj-allpass", rbj_allpass())
    HANDLE_CASE("invalid-parameters", invalid_parameter_case())

#undef HANDLE_CASE
    return 2;
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::cerr << "expected one test-case name\n";
        return 2;
    }

    const int result = dispatch(argv[1]);
    if (result == 0) {
        std::cout << "PASS " << argv[1] << '\n';
    } else if (result == 2) {
        std::cerr << "unknown test case: " << argv[1] << '\n';
    } else {
        std::cerr << "FAIL " << argv[1] << " result=" << result << '\n';
    }
    return result;
}
