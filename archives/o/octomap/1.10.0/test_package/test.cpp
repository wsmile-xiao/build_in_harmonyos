#include <stdint.h>
#include <stddef.h>
#include <octomap/octomap.h>
#include <octomap/math/Pose6D.h>
#include <octomap/math/Quaternion.h>
#include <octomap/math/Vector3.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

// octomap 1.10.0 —— 真实占据栅格计算验证（非 dlopen 空壳）。
// 本包产**两个**库，两个都必须被真实调用，否则其中一个坏了不会被发现：
//   liboctomath  —— ① Vector3 / Quaternion / Pose6D 的旋转与位姿复合
//   liboctomap   —— ② 建树插点、③ 光线投射穿透自由空间、④ 二进制序列化往返
//
// 数值断言用闭式解对账（绕 Z 轴 90° 把 (1,0,0) 转到 (0,1,0)），不是"跑起来不崩"。

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

static bool near(double a, double b, double eps = 1e-4) {
  return std::fabs(a - b) < eps;
}

int main() {
  // ───────────────────────── ① liboctomath ─────────────────────────
  {
    using octomath::Pose6D;
    using octomath::Quaternion;
    using octomath::Vector3;

    Vector3 v(1.0f, 0.0f, 0.0f);
    CHECK(near(v.norm(), 1.0), "Vector3::norm 单位向量");

    Vector3 w(0.0f, 2.0f, 0.0f);
    CHECK(near(v.dot(w), 0.0), "Vector3::dot 正交向量点积为 0");
    Vector3 c = v.cross(w);
    CHECK(near(c.x(), 0.0) && near(c.y(), 0.0) && near(c.z(), 2.0),
          "Vector3::cross 叉积 = (0,0,2)");

    // 绕 Z 轴 90°：(1,0,0) → (0,1,0)
    Quaternion q(0.0, 0.0, M_PI / 2.0);   // roll, pitch, yaw
    Vector3 r = q.rotate(v);
    CHECK(near(r.x(), 0.0) && near(r.y(), 1.0) && near(r.z(), 0.0),
          "Quaternion 绕 Z 转 90°：(1,0,0)→(0,1,0)");

    // 位姿复合：先转 90° 再平移 (0,0,1)
    Pose6D p(Vector3(0.0f, 0.0f, 1.0f), q);
    Vector3 t = p.transform(v);
    CHECK(near(t.x(), 0.0) && near(t.y(), 1.0) && near(t.z(), 1.0),
          "Pose6D::transform 旋转+平移复合正确");

    // 逆变换应还原
    Vector3 back = p.inv().transform(t);
    CHECK(near(back.x(), 1.0) && near(back.y(), 0.0) && near(back.z(), 0.0),
          "Pose6D::inv 逆变换还原原点");
  }

  // ───────────────────────── ② liboctomap 建树 ─────────────────────────
  const double res = 0.1;
  octomap::OcTree tree(res);
  CHECK(near(tree.getResolution(), res), "OcTree 分辨率读回一致");
  CHECK(tree.size() == 0, "新建树为空");

  // 标一个占据、一个自由
  octomap::point3d occ(1.0f, 1.0f, 1.0f);
  octomap::point3d fre(2.0f, 2.0f, 2.0f);
  for (int i = 0; i < 10; ++i) {          // 多次观测把 log-odds 顶到饱和
    tree.updateNode(occ, true);
    tree.updateNode(fre, false);
  }

  octomap::OcTreeNode *n_occ = tree.search(occ);
  octomap::OcTreeNode *n_fre = tree.search(fre);
  CHECK(n_occ != nullptr, "search 找得到已标记的占据体素");
  CHECK(n_fre != nullptr, "search 找得到已标记的自由体素");
  CHECK(n_occ && tree.isNodeOccupied(n_occ), "占据体素判为 occupied");
  CHECK(n_fre && !tree.isNodeOccupied(n_fre), "自由体素判为 free");
  if (n_occ && n_fre)
    CHECK(n_occ->getOccupancy() > n_fre->getOccupancy(),
          "占据概率 > 自由概率（log-odds 更新真的生效）");

  // 从未观测过的位置应当是 unknown（search 返回 NULL）
  CHECK(tree.search(octomap::point3d(50.0f, 50.0f, 50.0f)) == nullptr,
        "未观测区域 search 返回 NULL（unknown）");
  CHECK(tree.size() > 0, "树节点数 > 0");

  // ───────────────────────── ③ 光线投射 ─────────────────────────
  {
    octomap::OcTree rt(res);
    octomap::point3d origin(0.0f, 0.0f, 0.0f);
    octomap::point3d hit(3.0f, 0.0f, 0.0f);
    for (int i = 0; i < 10; ++i) rt.insertRay(origin, hit);

    // 端点应占据，路径中点应被清成自由
    octomap::OcTreeNode *e = rt.search(hit);
    octomap::OcTreeNode *m = rt.search(octomap::point3d(1.5f, 0.0f, 0.0f));
    CHECK(e && rt.isNodeOccupied(e), "insertRay 端点标为 occupied");
    CHECK(m && !rt.isNodeOccupied(m), "insertRay 路径中点被清为 free");

    // castRay 从原点朝 +x 打，应命中端点附近
    octomap::point3d end;
    const bool got = rt.castRay(origin, octomap::point3d(1.0f, 0.0f, 0.0f), end,
                                true /*ignoreUnknown*/, 10.0);
    CHECK(got, "castRay 命中占据体素");
    if (got)
      CHECK(near(end.x(), 3.0, res * 2), "castRay 命中点 x≈3.0（±2 体素）");
  }

  // ───────────────────────── ④ 二进制序列化往返 ─────────────────────────
  {
    const std::string path = "probe_tree.bt";
    CHECK(tree.writeBinary(path), "writeBinary 写出成功");

    octomap::OcTree back(res);
    CHECK(back.readBinary(path), "readBinary 读回成功");
    CHECK(near(back.getResolution(), res), "往返后分辨率保真");

    octomap::OcTreeNode *b_occ = back.search(occ);
    octomap::OcTreeNode *b_fre = back.search(fre);
    CHECK(b_occ && back.isNodeOccupied(b_occ), "往返后占据体素仍为 occupied");
    CHECK(b_fre && !back.isNodeOccupied(b_fre), "往返后自由体素仍为 free");
    std::remove(path.c_str());
  }

  if (failures) {
    std::fprintf(stderr, "\noctomap: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\noctomap 1.10.0: 全部断言通过（liboctomap + liboctomath 均已真实调用）\n");
  return 0;
}
