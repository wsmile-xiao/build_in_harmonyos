#include <2geom/bezier.h>
#include <2geom/point.h>
#include <2geom/svg-path-parser.h>
#include <2geom/pathvector.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/utsname.h>
#include <unistd.h>

static unsigned assertions = 0;
#define CHECK(expr) do { ++assertions; if (!(expr)) { std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #expr); return 1; } } while (0)
int main() {
    utsname os{};
    CHECK(uname(&os) == 0);
    CHECK(std::strcmp(os.sysname, "HarmonyOS") == 0);
    Geom::Bezier hump(0., 1., 0.);
    CHECK(std::fabs(hump.valueAt(0.)) < 1e-12);
    CHECK(std::fabs(hump.valueAt(.5) - .5) < 1e-12);
    CHECK(std::fabs(hump.valueAt(1.)) < 1e-12);
    Geom::Point p(1., 2.);
    CHECK(p[Geom::X] == 1.);
    CHECK(p[Geom::Y] == 2.);
    Geom::Point q = p + Geom::Point(3., 4.);
    CHECK(q[Geom::X] == 4.);
    CHECK(q[Geom::Y] == 6.);
    const char svg[] = "M 0,0 L 3,0 L 3,4 Z";
    Geom::PathVector paths = Geom::parse_svg_path(svg);
    CHECK(paths.size() == 1);
    CHECK(paths.front().closed());
    const char *tmp = std::getenv("TMPDIR");
    CHECK(tmp && *tmp);
    std::string file = std::string(tmp) + "/lib2geom-XXXXXX";
    int fd = mkstemp(file.data());
    CHECK(fd >= 0);
    CHECK(write(fd, svg, sizeof(svg)) == sizeof(svg));
    char buffer[sizeof(svg)]{};
    CHECK(pread(fd, buffer, sizeof(buffer), 0) == sizeof(buffer));
    CHECK(std::memcmp(svg, buffer, sizeof(svg)) == 0);
    CHECK(close(fd) == 0);
    CHECK(unlink(file.c_str()) == 0);
    std::printf("CONSUMER_1_OF_1_PASS assertions=%u parsed_paths=%zu\n", assertions, paths.size());
}
