#include <cairomm/context.h>
#include <cairomm/surface.h>
#include <cassert>
#include <cstdio>

int main(void) {
    Cairo::RefPtr<Cairo::ImageSurface> surface =
        Cairo::ImageSurface::create(Cairo::FORMAT_ARGB32, 64, 64);
    Cairo::RefPtr<Cairo::Context> cr = Cairo::Context::create(surface);
    cr->set_source_rgb(1.0, 0.0, 0.0);
    cr->rectangle(0, 0, 32, 32);
    cr->fill();
    assert(surface->get_width() == 64);
    assert(surface->get_height() == 64);
    printf("test cairomm 1.14.5: OK (surface %dx%d)\n",
           surface->get_width(), surface->get_height());
    return 0;
}
