/*****************************************************************************
 * test_package — mapnik 4.2.2 consumer smoke test (HarmonyOS PC)
 *
 * Exercises the public mapnik API surface: version macros, Map object,
 * layer management, datasource parameters, memory datasource feature
 * insertion, agg rendering and PNG output through the image pipeline.
 *****************************************************************************/
#include <mapnik/map.hpp>
#include <mapnik/layer.hpp>
#include <mapnik/datasource.hpp>
#include <mapnik/memory_datasource.hpp>
#include <mapnik/feature_factory.hpp>
#include <mapnik/geometry.hpp>
#include <mapnik/agg_renderer.hpp>
#include <mapnik/image.hpp>
#include <mapnik/image_util.hpp>
#include <mapnik/value.hpp>
#include <mapnik/version.hpp>

#include <cstdio>
#include <fstream>
#include <string>

int main()
{
    // 1. version sanity (MAPNIK_*_VERSION are plain C macros)
    if (MAPNIK_MAJOR_VERSION != 4 || MAPNIK_MINOR_VERSION != 2)
    {
        std::fprintf(stderr, "unexpected mapnik version: %d.%d.%d\n",
                     MAPNIK_MAJOR_VERSION, MAPNIK_MINOR_VERSION, MAPNIK_PATCH_VERSION);
        return 1;
    }
    std::printf("mapnik version: %d.%d.%d\n", MAPNIK_MAJOR_VERSION,
                MAPNIK_MINOR_VERSION, MAPNIK_PATCH_VERSION);

    // 2. map setup
    mapnik::Map m(256, 256);
    m.set_background(mapnik::color(240, 244, 248));

    // 3. memory datasource with one polygon feature
    mapnik::parameters params;
    params["type"] = "memory";
    auto ds = std::make_shared<mapnik::memory_datasource>(params);

    mapnik::context_ptr ctx = std::make_shared<mapnik::context_type>();
    ctx->push("name");
    mapnik::feature_ptr f = mapnik::feature_factory::create(ctx, 1);
    mapnik::geometry::polygon<double> poly;
    poly.emplace_back();
    auto& ring = poly.back();
    ring.emplace_back(16, 16);
    ring.emplace_back(240, 16);
    ring.emplace_back(240, 200);
    ring.emplace_back(16, 200);
    ring.emplace_back(16, 16);
    f->set_geometry(std::move(poly));
    f->put("name", mapnik::value_unicode_string("HarmonyOS PC"));
    ds->push(f);

    // 4. layer + render
    mapnik::layer lyr("test-layer");
    lyr.set_datasource(ds);
    m.add_layer(lyr);
    m.zoom_all();

    mapnik::image_rgba8 im(256, 256);
    mapnik::agg_renderer<mapnik::image_rgba8> ren(m, im);
    ren.apply();

    // 5. encode PNG (exercises the png/zlib pipeline)
    std::string out = "mapnik-test-out.png";
    mapnik::save_to_file(im, out, "png");

    std::ifstream check(out.c_str(), std::ios::binary);
    if (!check.good())
    {
        std::fprintf(stderr, "failed to write %s\n", out.c_str());
        return 1;
    }
    char magic[8] = {0};
    check.read(magic, 8);
    // PNG signature: 89 50 4E 47 0D 0A 1A 0A
    if (static_cast<unsigned char>(magic[0]) != 0x89 || magic[1] != 'P' ||
        magic[2] != 'N' || magic[3] != 'G')
    {
        std::fprintf(stderr, "output is not a PNG\n");
        return 1;
    }
    std::remove(out.c_str());

    std::printf("test_package: mapnik map rendered to PNG OK\n");
    return 0;
}
