// test_vtzero.cpp — L1 smoke test for vtzero header-only library
//
// Builds a minimal vector tile encode/decode round-trip using the public
// vtzero API (tile_builder + point_feature_builder, then vector_tile
// decode) to prove the headers compile and function correctly.
#include <vtzero/builder.hpp>
#include <vtzero/vector_tile.hpp>

#include <cstdint>
#include <iostream>
#include <string>

int main() {
    // 1) Encode: build a tile with one layer "roads" and one point feature.
    std::string buffer;
    {
        vtzero::tile_builder tile;
        vtzero::layer_builder layer{tile, "roads"};
        {
            vtzero::point_feature_builder feature{layer};
            feature.set_id(1);
            feature.add_point(10, 10);
            feature.commit();
        }
        tile.serialize(buffer);
    }
    if (buffer.empty()) {
        std::cerr << "FAIL: serialized tile is empty" << std::endl;
        return 1;
    }

    // 2) Decode: read the tile back and verify the layer name.
    vtzero::vector_tile tile{buffer};
    auto layer = tile.next_layer();
    if (!layer) {
        std::cerr << "FAIL: no layer decoded" << std::endl;
        return 1;
    }
    std::string name = std::string(layer.name().data(), layer.name().size());
    if (name != "roads") {
        std::cerr << "FAIL: unexpected layer name '" << name << "'" << std::endl;
        return 1;
    }

    if (layer.num_features() != 1) {
        std::cerr << "FAIL: expected 1 feature, got " << layer.num_features()
                  << std::endl;
        return 1;
    }

    std::cout << "PASS: vtzero encode/decode round-trip OK (layer='" << name
              << "', features=" << layer.num_features()
              << ", tile_bytes=" << buffer.size() << ")" << std::endl;
    return 0;
}