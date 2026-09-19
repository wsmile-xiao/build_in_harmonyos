// Installed-package consumer test for libnoise 1.0.0.
//
// Links against the packaged library and exercises the public API contract
// with 16 assertions: deterministic/finite/coherent Perlin sampling,
// parameter setters, the Billow and RidgedMulti generators, module graph
// wiring through ScaleBias, the ExceptionNoModule contract, the four model
// classes and the LatLonToXYZ helper.  Returns non-zero if any check fails.

#include <cmath>
#include <cstdio>

#include <noise/noise.h>
#include <noise/latlon.h>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool condition, const char* what)
{
    ++g_checks;
    if (!condition) {
        ++g_failures;
        std::printf("FAIL: %s\n", what);
    }
}

}  // namespace

int main()
{
    const double px = 0.375;
    const double py = 0.625;
    const double pz = 0.875;

    // 1. Perlin: deterministic, finite, coherent.
    noise::module::Perlin perlin;
    const double a = perlin.GetValue(px, py, pz);
    check(a == perlin.GetValue(px, py, pz), "perlin sampling is deterministic");
    check(std::isfinite(a), "perlin sample is finite");
    const double nearby = perlin.GetValue(px + 0.001, py, pz);
    check(std::fabs(nearby - a) < 0.05,
          "perlin is coherent: a small input change yields a small output change");
    check(perlin.GetValue(120.75, -44.125, 302.5) != a,
          "perlin separates distant input coordinates");

    // 2. Parameter setters are accepted and change the generated field.
    perlin.SetOctaveCount(6);
    perlin.SetFrequency(2.0);
    perlin.SetPersistence(0.5);
    perlin.SetLacunarity(2.0);
    perlin.SetNoiseQuality(noise::QUALITY_BEST);
    const double configured = perlin.GetValue(px, py, pz);
    check(std::isfinite(configured), "configured perlin sample is finite");
    check(configured != a, "perlin configuration changes the sampled field");

    // 3. Multifractal generators.
    noise::module::Billow billow;
    billow.SetOctaveCount(4);
    check(std::isfinite(billow.GetValue(1.25, 2.5, 3.75)), "billow sample is finite");
    noise::module::RidgedMulti ridged;
    ridged.SetOctaveCount(5);
    check(std::isfinite(ridged.GetValue(-2.5, 7.125, 0.0625)),
          "ridged multifractal sample is finite");

    // 4. Module graph: ScaleBias must apply source*scale+bias exactly.
    noise::module::Perlin source;
    noise::module::ScaleBias scaled;
    scaled.SetSourceModule(0, source);
    scaled.SetScale(2.0);
    scaled.SetBias(1.0);
    const double sv = source.GetValue(px, py, pz);
    check(scaled.GetValue(px, py, pz) == sv * 2.0 + 1.0,
          "scalebias applies source*scale+bias exactly");

    // 5. Exception contract: reading an unconnected source module throws.
    bool threw = false;
    try {
        noise::module::Perlin orphan;
        orphan.GetSourceModule(0);
    } catch (const noise::ExceptionNoModule&) {
        threw = true;
    }
    check(threw, "unconnected GetSourceModule raises ExceptionNoModule");

    // 6. Model layer maps geometry through a noise module.
    noise::module::Perlin basisModule;
    noise::model::Sphere sphere(basisModule);
    check(std::isfinite(sphere.GetValue(30.0, -45.0)), "sphere model sample is finite");
    noise::model::Cylinder cylinder(basisModule);
    check(std::isfinite(cylinder.GetValue(1.5, 2.25)), "cylinder model sample is finite");
    noise::model::Plane plane(basisModule);
    check(std::isfinite(plane.GetValue(0.5, -1.25)), "plane model sample is finite");
    noise::model::Line line(basisModule);
    line.SetStartPoint(0.0, 0.0, 0.0);
    line.SetEndPoint(3.0, 4.0, 5.0);
    check(std::isfinite(line.GetValue(0.5)), "line model sample is finite at midpoint");

    // 7. Geographic helper: LatLonToXYZ stays on the unit sphere.
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
    noise::LatLonToXYZ(0.0, 0.0, x, y, z);
    check(std::fabs(x - 1.0) < 1e-12 && std::fabs(y) < 1e-12 && std::fabs(z) < 1e-12,
          "LatLonToXYZ(0,0) maps to (1,0,0)");
    noise::LatLonToXYZ(37.5, -122.25, x, y, z);
    check(std::fabs(std::sqrt(x * x + y * y + z * z) - 1.0) < 1e-12,
          "LatLonToXYZ stays on the unit sphere");

    std::printf("libnoise consumer test: %d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
