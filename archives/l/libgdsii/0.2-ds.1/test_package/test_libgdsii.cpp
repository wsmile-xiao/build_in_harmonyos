// Consumer test: use libGDSII exactly like a downstream library user would.
// Parses the upstream example GDSII file (examples/bend-flux/bend-flux.gds)
// through the public API and asserts on the extracted geometry.
#include "bend_flux_gds.h"
#include "libGDSII.h"

#include <cstdio>
#include <fstream>

int main() {
    /* Materialize the embedded upstream asset for the parser. */
    std::ofstream f("bend-flux.gds", std::ios::binary);
    f.write(reinterpret_cast<const char *>(bend_flux_gds),
            static_cast<std::streamsize>(bend_flux_gds_len));
    f.close();

    libGDSII::GDSIIData data("bend-flux.gds");

    // bend-flux.gds (upstream examples/bend-flux) ground truth, measured on
    // a native reference run: layers 0..6, 7 polygons, 1 polygon on layer 0,
    // 1 text string.
    iVec layers = data.GetLayers();
    if (layers.size() != 7) {
        std::printf("FAIL: expected 7 layers, got %zu\n", layers.size());
        return 1;
    }
    for (int i = 0; i < 7; ++i) {
        if (layers[i] != i) {
            std::printf("FAIL: expected layer %d at index %d, got %d\n",
                        i, i, layers[i]);
            return 1;
        }
    }
    std::printf("layers 0..6 as expected\n");

    PolygonList all = data.GetPolygons(-1);
    if (all.size() != 7) {
        std::printf("FAIL: expected 7 polygons on all layers, got %zu\n",
                    all.size());
        return 1;
    }
    if (all[0].size() < 6) {
        std::printf("FAIL: first polygon has fewer than 3 vertices\n");
        return 1;
    }
    std::printf("polygons on all layers: %zu (first has %zu coords)\n",
                all.size(), all[0].size());

    PolygonList onLayer = data.GetPolygons(layers[0]);
    if (onLayer.size() != 1) {
        std::printf("FAIL: expected 1 polygon on layer %d, got %zu\n",
                    layers[0], onLayer.size());
        return 1;
    }
    std::printf("polygons on layer %d: %zu\n", layers[0], onLayer.size());

    TextStringList texts = data.GetTextStrings(-1);
    if (texts.size() != 1) {
        std::printf("FAIL: expected 1 text string, got %zu\n", texts.size());
        return 1;
    }
    std::printf("text strings: %zu\n", texts.size());

    std::printf("consumer test passed\n");
    return 0;
}
