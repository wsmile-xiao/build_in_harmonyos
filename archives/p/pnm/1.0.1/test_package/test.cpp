#include <cstdio>
#include <pnm.hpp>

int main()
{
    using namespace pnm::literals;
    pnm::image<pnm::rgb_pixel> image(2, 1);
    image[0][0] = 0xFF0000_rgb;
    image[0][1] = 0x0000FF_rgb;

    const char *path = "pnm_consumer_test.ppm";
    pnm::write(path, image, pnm::format::binary);
    const auto loaded = pnm::read(path);
    if (loaded.width() != 2) return 1;
    if (loaded.height() != 1) return 2;
    if (loaded[0][0].red != 255) return 3;
    if (loaded[0][1].blue != 255) return 4;
    std::remove(path);
    return 0;
}
