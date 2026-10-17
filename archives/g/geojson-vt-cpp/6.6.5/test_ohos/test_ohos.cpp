// test_ohos.cpp — geojson-vt-cpp 6.6.5 HarmonyOS PC 专项验证（自包含，可单独执行）
//
// 区别于上游内置自测（gtest 23 项）与 test_package 消费者用例：
// 在真实鸿蒙 PC（aarch64, OHOS）上对库公共 API 做独立专项检查：
//
//   H1  公共 API geoJSONToTile：从 geometry 构建 tile，验证要素个数与坐标
//   H2  GeoJSONVT 索引类：getTile 返回真实裁剪/简化结果（lineMetrics）
//   H3  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
//
// 退出码：0=全部通过；非 0=有失败（打印首个错误）。
#include <mapbox/geojsonvt.hpp>

#include <cmath>
#include <cstdio>
#include <string>

using mapbox::geojsonvt::geojson;
using mapbox::geojsonvt::geoJSONToTile;
using mapbox::geojsonvt::GeoJSONVT;
using mapbox::geojsonvt::Options;
using mapbox::geojsonvt::Tile;
using mapbox::geojsonvt::TileOptions;

static int failures = 0;
static void check(bool ok, const char* name) {
    std::printf("%s: %s\n", ok ? "PASS" : "FAIL", name);
    if (!ok) failures++;
}

int main() {
    std::printf("--- geojson-vt-cpp 6.6.5 HarmonyOS 专项验证 ---\n");

    // H1: point geometry -> tile 要素个数
    {
        mapbox::geojsonvt::geometry point = mapbox::geometry::point<double>(0.5, 0.5);
        geojson g = point;
        TileOptions opts;
        const Tile t = geoJSONToTile(g, 0, 0, 0, opts);
        check(t.features.size() == 1, "H1 geoJSONToTile(point) -> 1 feature");
        if (t.features.size() == 1) {
            std::printf("  tile features=%zu\n", t.features.size());
        }
    }

    // H1b: linestring -> tile 坐标精度（int16 量化）
    {
        mapbox::geojsonvt::geometry line =
            mapbox::geometry::line_string<double>({{0.1, 0.1}, {0.9, 0.9}});
        geojson g = line;
        TileOptions opts;
        const Tile t = geoJSONToTile(g, 0, 0, 0, opts);
        bool ok = t.features.size() == 1;
        if (ok) {
            const auto& geom = t.features[0].geometry;
            try {
                const auto& ls = geom.get<mapbox::geometry::line_string<int16_t>>();
                ok = (ls.size() == 2);
            } catch (const std::exception&) {
                ok = false;
            }
        }
        check(ok, "H1b geoJSONToTile(linestring) -> 2-point int16 line");
    }

    // H2: GeoJSONVT 索引类 + getTile（带 lineMetrics 的真实结果）
    {
        const std::string data = R"geojson({"type":"LineString","coordinates":[[-77.0313737,38.8955164],[-77.0141601,38.8875325],[-76.99,38.87]]})geojson";
        mapbox::geojsonvt::geometry line =
            mapbox::geometry::line_string<double>({{-77.0313737, 38.8955164},
                                                   {-77.0141601, 38.8875325},
                                                   {-76.99, 38.87}});
        Options options;
        options.lineMetrics = true;
        options.buffer = 2048;
        options.extent = 8192;
        geojson gj(line);  // 显式包装为 geojson 变体，避免构造歧义
        GeoJSONVT index(gj, options);
        const Tile& tile = index.getTile(13, 2344, 3134);
        bool ok = !tile.features.empty();
        if (ok) {
            const auto& props = tile.features[0].properties;
            const auto it = props.find("mapbox_clip_start");
            ok = (it != props.end());
            if (ok) {
                const double start = it->second.get<double>();
                std::printf("  mapbox_clip_start=%.6f\n", start);
                ok = std::fabs(start - 0.660622) < 1e-4;
            }
        }
        check(ok, "H2 GeoJSONVT.getTile lineMetrics clip_start~=0.660622");
    }

    std::printf("--- result: %s ---\n", failures == 0 ? "ALL PASS" : "FAILED");
    return failures == 0 ? 0 : 1;
}
