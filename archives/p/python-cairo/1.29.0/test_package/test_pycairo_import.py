import io
import os
import sys

staged_site_packages = os.environ.get("PYCAIRO_STAGED_SITE_PACKAGES")
if staged_site_packages:
    sys.path.insert(0, staged_site_packages)
import cairo


def main():
    version_info = tuple(int(part) for part in cairo.version.split(".")[:3])
    assert version_info >= (1, 15, 10)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 16, 16)
    context = cairo.Context(surface)
    context.set_source_rgb(0.2, 0.4, 0.8)
    context.paint()
    context.set_source_rgb(1.0, 1.0, 1.0)
    context.rectangle(4, 4, 8, 8)
    context.fill()
    assert surface.get_width() == 16
    assert surface.get_height() == 16
    output = io.BytesIO()
    surface.write_to_png(output)
    assert output.getvalue().startswith(b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    main()
