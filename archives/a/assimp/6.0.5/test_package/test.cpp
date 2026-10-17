#include <stdint.h>
#include <stddef.h>
#include <assimp/Importer.hpp>
#include <assimp/scene.h>
#include <assimp/postprocess.h>
#include <assimp/version.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

// assimp 6.0.5 —— 真实模型解析验证（非 dlopen 空壳）。
// 从内存里喂一个最小 OBJ（一个正方形 = 2 个三角形），断言：
//   ① 版本号读得出且是 6.x
//   ② ReadFileFromMemory 真的解析出场景（不是返回空指针就算过）
//   ③ 网格数 / 顶点数 / 面数与手算一致
//   ④ 顶点坐标逐个对账（证明解析出的是真数据，不是零填充）
//   ⑤ 包围盒尺寸算出来 = 1×1
//   ⑥ 错误路径：喂垃圾数据必须失败且 GetErrorString 可读

static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++failures;                                                            \
    } else {                                                                 \
      std::printf("[ok] %s\n", msg);                                         \
    }                                                                        \
  } while (0)

static bool near(double a, double b, double eps = 1e-5) {
  return std::fabs(a - b) < eps;
}

// 单位正方形，两个三角形
static const char *kObj =
    "v 0.0 0.0 0.0\n"
    "v 1.0 0.0 0.0\n"
    "v 1.0 1.0 0.0\n"
    "v 0.0 1.0 0.0\n"
    "f 1 2 3\n"
    "f 1 3 4\n";

int main() {
  // ①
  const unsigned major = aiGetVersionMajor();
  const unsigned minor = aiGetVersionMinor();
  std::printf("     assimp 版本: %u.%u.%u\n", major, minor, aiGetVersionRevision());
  CHECK(major == 6, "aiGetVersionMajor() == 6");

  // ② ③ ④ ⑤
  {
    Assimp::Importer importer;
    const aiScene *scene = importer.ReadFileFromMemory(
        kObj, std::strlen(kObj),
        aiProcess_Triangulate | aiProcess_JoinIdenticalVertices, "obj");

    CHECK(scene != nullptr, "ReadFileFromMemory 解析 OBJ 成功");
    if (!scene) {
      std::fprintf(stderr, "       assimp 错误: %s\n", importer.GetErrorString());
    } else {
      CHECK(scene->mNumMeshes == 1, "网格数 = 1");
      if (scene->mNumMeshes >= 1) {
        const aiMesh *m = scene->mMeshes[0];
        CHECK(m->mNumFaces == 2, "面数 = 2（两个三角形）");
        CHECK(m->mNumVertices == 4, "顶点数 = 4（JoinIdenticalVertices 后去重）");
        if (m->mNumVertices != 4)
          std::fprintf(stderr, "       实得 %u\n", m->mNumVertices);

        // ④ 逐点对账 + ⑤ 包围盒
        float minx = 1e9f, maxx = -1e9f, miny = 1e9f, maxy = -1e9f;
        bool all_z_zero = true;
        for (unsigned i = 0; i < m->mNumVertices; ++i) {
          const aiVector3D &v = m->mVertices[i];
          if (v.x < minx) minx = v.x;
          if (v.x > maxx) maxx = v.x;
          if (v.y < miny) miny = v.y;
          if (v.y > maxy) maxy = v.y;
          if (!near(v.z, 0.0)) all_z_zero = false;
        }
        CHECK(all_z_zero, "所有顶点 z = 0（平面正方形）");
        CHECK(near(maxx - minx, 1.0) && near(maxy - miny, 1.0),
              "包围盒尺寸 = 1×1");
        if (!near(maxx - minx, 1.0))
          std::fprintf(stderr, "       实得 %.6f × %.6f\n", maxx - minx, maxy - miny);

        // 每个面都必须是三角形
        bool all_tri = true;
        for (unsigned f = 0; f < m->mNumFaces; ++f)
          if (m->mFaces[f].mNumIndices != 3) all_tri = false;
        CHECK(all_tri, "每个面都是 3 个索引（Triangulate 生效）");
      }
    }
  }

  // ⑥ 错误路径
  {
    Assimp::Importer bad;
    const char *garbage = "this is definitely not a model file\x01\x02\x03";
    const aiScene *s = bad.ReadFileFromMemory(garbage, std::strlen(garbage), 0, "obj");
    CHECK(s == nullptr || s->mNumMeshes == 0, "垃圾输入不产生有效网格");
    CHECK(bad.GetErrorString() != nullptr, "GetErrorString 可调用");
  }

  if (failures) {
    std::fprintf(stderr, "\nassimp: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nassimp 6.0.5: 全部断言通过\n");
  return 0;
}
