#include <cairomm/context.h>
#include <cairomm/surface.h>
#include <cstdio>

int main(void) {
    Cairo::RefPtr<Cairo::ImageSurface> surface =
        Cairo::ImageSurface::create(Cairo::ImageSurface::Format::ARGB32, 64, 64);
    Cairo::RefPtr<Cairo::Context> cr = Cairo::Context::create(surface);
    cr->set_source_rgb(1.0, 0.0, 0.0);
    cr->rectangle(0, 0, 32, 32);
    cr->fill();
    int width = surface->get_width();
    int height = surface->get_height();
    if (width != 64 || height != 64) {
        std::fprintf(stderr, "cairomm 1.16.2 test FAILED: surface size %dx%d, expected 64x64\n",
                     width, height);
        return 1;
    }
    std::printf("test cairomm 1.16.2: OK (surface %dx%d)\n", width, height);
    return 0;
}