// test_package consumer test — gplotpp 1.1.0
//
// A real consumer of the installed package: it includes only the public
// header gplot++.h (installed at <pkg>/include), uses the public
// Gnuplot API, links the normal gplotpp::gplotpp CMake target and runs
// the produced binary against a real `gnuplot` executable. It then
// verifies the observable plot output (labels present in the "dumb"
// terminal render) instead of only printing a string.
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>
#include <chrono>
#include <vector>

#include "gplot++.h"

namespace {

std::string read_file(const char *path) {
    std::ifstream in(path, std::ios::binary);
    std::stringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

}  // namespace

int main() {
    const std::string out_file{"consumer_plot.svg"};

    {
        Gnuplot plt{};
        if (!plt.redirect_to_svg(out_file, "800,600")) {
            std::fprintf(stderr, "FAIL: redirect_to_svg failed (gnuplot not usable?)\n");
            return 1;
        }

        std::vector<double> x{1, 2, 3, 4, 5};
        std::vector<double> y{5, 4, 3, 2, 1};
        plt.plot(x, y, "ConsumerSeries", Gnuplot::LineStyle::POINTS);
        plt.set_xlabel("ConsumerX");
        plt.set_ylabel("ConsumerY");
        if (!plt.show()) {
            std::fprintf(stderr, "FAIL: show() failed\n");
            return 2;
        }
    }

    // Gnuplot must have finished writing the SVG file by the time the pipe
    // is closed; give it a moment before reading it back.
    std::this_thread::sleep_for(std::chrono::milliseconds(1200));

    const std::string content = read_file(out_file.c_str());
    if (content.empty()) {
        std::fprintf(stderr, "FAIL: plot output file is empty\n");
        return 3;
    }
    if (content.find("ConsumerSeries") == std::string::npos) {
        std::fprintf(stderr, "FAIL: plot output misses series label\n");
        return 4;
    }
    if (content.find("ConsumerX") == std::string::npos ||
        content.find("ConsumerY") == std::string::npos) {
        std::fprintf(stderr, "FAIL: plot output misses axis labels\n");
        return 5;
    }

    std::printf("PASS: gplotpp consumer plot rendered and labels verified\n");
    return 0;
}