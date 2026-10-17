// tinyobjloader consumer test — 在单一翻译单元定义 TINYOBJLOADER_IMPLEMENTATION
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
  std::string basepath = "";
  std::string objfile = "cube.obj";
  if (argc > 1) {
    objfile = argv[1];
  }

  tinyobj::attrib_t attrib;
  std::vector<tinyobj::shape_t> shapes;
  std::vector<tinyobj::material_t> materials;
  std::string warn;
  std::string err;

  bool ret = tinyobj::LoadObj(&attrib, &shapes, &materials, &warn, &err,
                              objfile.c_str(), basepath.c_str());
  CHECK(ret, "LoadObj should succeed on cube.obj");
  CHECK(shapes.size() >= 1, "cube.obj should parse at least one shape");
  CHECK(attrib.vertices.size() >= 24,
        "cube.obj should contain at least 24 vertex components (8 verts x 3)");
  // 短路守卫：仅当至少解析出一个 shape 时才访问 shapes[0]，
  // 避免 LoadObj 失败且 shapes 为空时对空容器做下标访问（未定义行为并掩盖诊断）。
  CHECK(shapes.size() >= 1 && shapes[0].mesh.indices.size() >= 36,
        "cube.obj should contain at least 36 indices (12 tris x 3)");

  if (failures != 0) {
    std::fprintf(stderr, "tinyobjloader consumer test failed: %d assertion(s)\n",
                 failures);
    return 1;
  }
  std::printf("tinyobjloader consumer test passed: LoadObj ok, shapes=%zu "
              "indices=%zu vertices=%zu\n",
              shapes.size(),
              shapes.empty() ? 0 : shapes[0].mesh.indices.size(),
              attrib.vertices.size());
  return 0;
}
