// test_consumer.cpp — geojson-vt-cpp 6.6.5 消费者验证用例
//
// 模拟业务上层组件：仅通过 geojson-vt-cpp 已安装/导出的公开头文件
// （<mapbox/geojsonvt.hpp>）与公开 API（geoJSONToTile / GeoJSONVT /
// Tile / TileOptions / Options）完成"GeoJSON 几何 → 矢量瓦片切片"，
// 断言可观察结果（要素个数、裁剪后线段坐标、lineMetrics 属性），
// 验证第三方使用者可编译、链接并正常运行。
#include <mapbox/geojsonvt.hpp>

#include <cmath>
#include <cstdio>

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
    std::printf("--- geojson-vt-cpp 6.6.5 consumer verification ---\n");

    // C1: point geometry -> tile 要素个数
    {
        mapbox::geojsonvt::geometry point = mapbox::geometry::point<double>(0.5, 0.5);
        geojson g = point;
        TileOptions opts;
        const Tile t = geoJSONToTile(g, 0, 0, 0, opts);
        check(t.features.size() == 1, "C1 geoJSONToTile(point) -> 1 feature");
    }

    // C2: linestring -> tile int16 量化线段
    {
        mapbox::geojsonvt::geometry line =
            mapbox::geometry::line_string<double>({{0.1, 0.1}, {0.9, 0.9}});
        geojson g = line;
        TileOptions opts;
        const Tile t = geoJSONToTile(g, 0, 0, 0, opts);
        bool ok = t.features.size() == 1;
        if (ok) {
            try {
                const auto& ls = t.features[0].geometry
                    .get<mapbox::geometry::line_string<int16_t>>();
                ok = (ls.size() == 2);
            } catch (const std::exception&) {
                ok = false;
            }
        }
        check(ok, "C2 geoJSONToTile(linestring) -> 2-point int16 line");
    }

    // C3: GeoJSONVT 索引类 + getTile 真实裁剪结果（lineMetrics）
    {
        mapbox::geojsonvt::geometry line =
            mapbox::geometry::line_string<double>({{-77.0313737, 38.8955164},
                                                   {-77.0141601, 38.8875325},
                                                   {-76.99, 38.87}});
        Options options;
        options.lineMetrics = true;
        options.buffer = 2048;
        options.extent = 8192;
        geojson gj(line);
        GeoJSONVT index(gj, options);
        const Tile& tile = index.getTile(13, 2344, 3134);
        bool ok = !tile.features.empty();
        if (ok) {
            const auto it = tile.features[0].properties.find("mapbox_clip_start");
            ok = (it != tile.features[0].properties.end());
            if (ok) {
                const double start = it->second.get<double>();
                std::printf("  mapbox_clip_start=%.6f\n", start);
                ok = std::fabs(start - 0.660622) < 1e-4;
            }
        }
        check(ok, "C3 GeoJSONVT.getTile lineMetrics clip_start~=0.660622");
    }

    std::printf("--- result: %s ---\n", failures == 0 ? "ALL PASS" : "FAILED");
    return failures == 0 ? 0 : 1;
}
