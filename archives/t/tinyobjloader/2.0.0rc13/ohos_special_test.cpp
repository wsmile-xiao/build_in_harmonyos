// HarmonyOS 专项测试：tinyobjloader 2.0.0rc13 真实消费入口验证
// 在单一翻译单元定义 TINYOBJLOADER_IMPLEMENTATION，用 OHOS armv8 工具链
// (clang 15 / aarch64-unknown-linux-ohos) 编译并实际运行。
#define TINYOBJLOADER_IMPLEMENTATION
#include "tiny_obj_loader.h"

#include <cstdio>
#include <string>
#include <vector>

#define CHECK(cond, msg)                                                       \
  do {                                                                         \
    if (!(cond)) {                                                             \
      std::fprintf(stderr, "FAIL: %s\n", msg);                                 \
      failures++;                                                              \
    }                                                                          \
  } while (0)

int main(int argc, char** argv) {
  int failures = 0;
  const char* objfile = (argc > 1) ? argv[1] : "cornell_box.obj";
  const char* mtlbase = (argc > 2) ? argv[2] : "";

  tinyobj::attrib_t attrib;
  std::vector<tinyobj::shape_t> shapes;
  std::vector<tinyobj::material_t> materials;
  std::string warn;
  std::string err;

  bool ret =
      tinyobj::LoadObj(&attrib, &shapes, &materials, &warn, &err, objfile,
                       mtlbase, /*triangulate=*/true);
  CHECK(ret, "LoadObj should succeed");
  CHECK(shapes.size() >= 1, "at least one shape parsed");
  CHECK(attrib.vertices.size() >= 9,
        "vertices present (>=3 verts x 3 comps)");
  CHECK(attrib.normals.size() >= 3 || attrib.texcoords.size() >= 2 ||
            attrib.vertices.size() > 0,
        "geometry data present");

  // 逐 shape 校验索引非空且合法
  for (size_t i = 0; i < shapes.size(); i++) {
    const auto& m = shapes[i].mesh;
    CHECK(!m.indices.empty(), "shape indices non-empty");
    for (size_t j = 0; j < m.indices.size(); j++) {
      int vi = m.indices[j].vertex_index;
      CHECK(vi >= 0 && (size_t)vi < attrib.vertices.size() / 3,
            "vertex index in range");
    }
  }

  if (failures != 0) {
    std::fprintf(stderr,
                 "tinyobjloader HarmonyOS special test FAILED: %d assertion(s)\n",
                 failures);
    return 1;
  }
  std::printf("tinyobjloader HarmonyOS special test passed: file=%s shapes=%zu "
              "vertices=%zu normals=%zu texcoords=%zu materials=%zu\n",
              objfile, shapes.size(), attrib.vertices.size(),
              attrib.normals.size(), attrib.texcoords.size(),
              materials.size());
  return 0;
}
