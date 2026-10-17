#include <png++/png.hpp>

#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>

namespace {

int checks = 0;

bool check(bool condition, const char* message)
{
    ++checks;
    if (!condition) {
        std::cerr << "check failed: " << message << '\n';
        return false;
    }
    return true;
}

bool pixels_equal(const png::rgb_pixel& lhs, const png::rgb_pixel& rhs)
{
    return lhs.red == rhs.red && lhs.green == rhs.green && lhs.blue == rhs.blue;
}

}  // namespace

int main()
{
    const std::string output_path = "pngpp-roundtrip.png";
    png::image<png::rgb_pixel> image(3, 2);
    const png::rgb_pixel expected[] = {
        png::rgb_pixel(255, 0, 0),
        png::rgb_pixel(0, 255, 0),
        png::rgb_pixel(0, 0, 255),
        png::rgb_pixel(255, 255, 255),
        png::rgb_pixel(17, 34, 51),
        png::rgb_pixel(0, 0, 0),
    };

    for (std::size_t y = 0; y < image.get_height(); ++y) {
        for (std::size_t x = 0; x < image.get_width(); ++x) {
            image[y][x] = expected[y * image.get_width() + x];
        }
    }
    image.write(output_path);

    bool ok = true;
    ok &= check(std::ifstream(output_path.c_str(), std::ios::binary).good(),
                "PNG file was created");

    png::image<png::rgb_pixel> decoded(output_path);
    ok &= check(decoded.get_width() == 3, "decoded width is 3");
    ok &= check(decoded.get_height() == 2, "decoded height is 2");

    for (std::size_t y = 0; y < decoded.get_height(); ++y) {
        for (std::size_t x = 0; x < decoded.get_width(); ++x) {
            ok &= check(pixels_equal(decoded[y][x],
                                     expected[y * decoded.get_width() + x]),
                        "decoded pixel matches the original");
        }
    }

    std::remove(output_path.c_str());
    if (!ok) {
        return 1;
    }

    std::cout << "png++ consumer assertions passed: " << checks << "/9\n";
    return checks == 9 ? 0 : 1;
}
