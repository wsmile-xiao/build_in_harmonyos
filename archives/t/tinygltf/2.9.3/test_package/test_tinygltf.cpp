/*
 * Consumer test for the installed tinygltf package.
 *
 * Compiles the header in implementation mode (TINYGLTF_IMPLEMENTATION)
 * and drives the real glTF 2.0 parser over an in-memory minimal glTF
 * asset, asserting actual parsed values. No external asset files needed.
 */
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

#define TINYGLTF_IMPLEMENTATION
#define STB_IMAGE_IMPLEMENTATION
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "tiny_gltf.h"

static int failures = 0;

static void check(bool cond, const char* what)
{
    if(cond)
        printf("PASS: %s\n", what);
    else
    {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

int main(void)
{
    // Minimal glTF 2.0 asset: one scene, one node, one mesh with a
    // POSITION primitive, backed by a base64 data-uri buffer of 12 bytes
    // (three float positions, all zero).
    const std::string gltf = R"({
  "asset": {"version": "2.0", "generator": "conan-consumer-test"},
  "scenes": [{"nodes": [0]}],
  "scene": 0,
  "nodes": [{"mesh": 0}],
  "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "mode": 4}]}],
  "buffers": [{
    "uri": "data:application/octet-stream;base64,AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "byteLength": 36
  }],
  "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36}],
  "accessors": [{
    "bufferView": 0, "componentType": 5126, "count": 3,
    "type": "VEC3", "min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]
  }]
})";

    tinygltf::Model model;
    std::string err;
    std::string warn;

    tinygltf::TinyGLTF loader;
    const bool ok = loader.LoadASCIIFromString(
        &model, &err, &warn, gltf.c_str(),
        static_cast<unsigned int>(gltf.size()),
        /*base_dir=*/"./", /*check_sections=*/0);

    check(ok, "minimal glTF parses without error");
    if(!ok)
    {
        printf("parse error: %s\n", err.c_str());
    }
    else
    {
        check(model.asset.version == "2.0",
            "asset version parsed as 2.0");
        check(model.scenes.size() == 1 && model.scenes[0].nodes.size() == 1
            && model.nodes[model.scenes[0].nodes[0]].mesh == 0,
            "scene graph resolves to node with mesh 0");
        check(model.meshes.size() == 1
            && model.meshes[0].primitives.size() == 1
            && model.meshes[0].primitives[0].attributes.count("POSITION") == 1,
            "mesh primitive carries POSITION attribute");
        check(model.accessors.size() == 1
            && model.accessors[0].componentType == TINYGLTF_COMPONENT_TYPE_FLOAT
            && model.accessors[0].count == 3
            && model.accessors[0].type == TINYGLTF_TYPE_VEC3,
            "accessor parses component type, count and VEC3 type");
    }

    if(failures != 0)
    {
        printf("%d check(s) FAILED\n", failures);
        return 1;
    }
    printf("all tinygltf consumer checks passed\n");
    return 0;
}
