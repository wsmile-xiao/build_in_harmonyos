#include <thorvg.h>

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <memory>

int main()
{
    constexpr uint32_t width = 32;
    constexpr uint32_t height = 32;
    uint32_t buffer[width * height] = {};

    if (tvg::Initializer::init(0) != tvg::Result::Success) return 1;
    auto canvas = tvg::SwCanvas::gen();
    auto shape = tvg::Shape::gen();
    if (!canvas || !shape) return 2;

    shape->appendRect(4.0f, 4.0f, 24.0f, 24.0f);
    shape->fill(255, 0, 0, 255);
    if (canvas->target(buffer, width, width, height,
                       tvg::ColorSpace::ARGB8888) != tvg::Result::Success) return 3;
    if (canvas->add(shape) != tvg::Result::Success) return 4;
    if (canvas->draw() != tvg::Result::Success) return 5;
    if (canvas->sync() != tvg::Result::Success) return 6;

    const bool rendered = std::any_of(std::begin(buffer), std::end(buffer),
                                      [](uint32_t pixel) { return pixel != 0; });
    tvg::Initializer::term();
    if (!rendered) return 7;
    std::cout << "ThorVG software rendering test passed\n";
    return 0;
}
