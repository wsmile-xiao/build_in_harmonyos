#include <stdint.h>
#include <stddef.h>
#include <libqhull_r/libqhull_r.h>
#include <libqhull_r/geom_r.h>      // qh_getarea 在这里，不在 libqhull_r.h
#include <libqhull_r/poly_r.h>      // qh_freeqhull / facetT 相关
#include <libqhull_r/mem_r.h>       // qh_memfreeshort

#include <cmath>
#include <cstdio>

// qhull 2020.2（上游 8.0.2）—— 真实凸包计算验证（非 dlopen 空壳）。
// 用闭式解对账，不是"跑起来不崩"：
//   ① 单位立方体 8 角 + 1 个内点 → 凸包顶点必须是 8（内点被正确剔除）
//   ② 体积 = 1.0，表面积 = 6.0（qh_getarea 真算出来的）
//   ③ 换一个已知形状（正四面体）再对一次体积，防止 ① 恰好蒙对
//   ④ qh_new_qhull 的返回码为 0
//
// 本包重做的直接动因：制品仓原有的 qhull 产物**无 SONAME**，
// 下游（coal）链接后 DT_NEEDED 会被烤成构建机的 conan cache 绝对路径。
// 故除断言外，产物核查还要确认 SONAME=libqhull_r.so.8.0（与上游 coal 所链一致）。

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

static bool near(double a, double b, double eps = 1e-6) {
  return std::fabs(a - b) < eps;
}

// 返回 0 表示成功；同时回填顶点数/面数/体积/表面积
static int hull(int dim, int n, coordT *pts, int *nvert, int *nfacet,
                double *vol, double *area) {
  qhT qh_qh;
  qhT *qh = &qh_qh;
  qh_zero(qh, stderr);
  char flags[] = "qhull ";
  int rc = qh_new_qhull(qh, dim, n, pts, /*ismalloc=*/0, flags, NULL, stderr);
  if (rc == 0) {
    qh_getarea(qh, qh->facet_list);      // 填 qh->totvol / qh->totarea
    *nvert = qh->num_vertices;
    *nfacet = qh->num_facets;
    *vol = qh->totvol;
    *area = qh->totarea;
  }
  int curlong = 0, totlong = 0;
  qh_freeqhull(qh, !qh_ALL);
  qh_memfreeshort(qh, &curlong, &totlong);
  if (curlong || totlong)
    std::fprintf(stderr, "[warn] qhull 内存未全部释放: %d %d\n", curlong, totlong);
  return rc;
}

int main() {
  // ① ② 单位立方体 8 角 + 1 个内点（0.5,0.5,0.5）
  {
    coordT pts[27] = {
        0, 0, 0,  1, 0, 0,  1, 1, 0,  0, 1, 0,
        0, 0, 1,  1, 0, 1,  1, 1, 1,  0, 1, 1,
        0.5, 0.5, 0.5,                       // 内点，不该进凸包
    };
    int nv = 0, nf = 0; double vol = 0, area = 0;
    int rc = hull(3, 9, pts, &nv, &nf, &vol, &area);
    CHECK(rc == 0, "qh_new_qhull 计算立方体凸包返回 0");
    if (rc == 0) {
      CHECK(nv == 8, "凸包顶点数为 8（内点被正确剔除）");
      if (nv != 8) std::fprintf(stderr, "       实得 %d\n", nv);
      CHECK(near(vol, 1.0, 1e-9), "凸包体积 = 1.0");
      if (!near(vol, 1.0, 1e-9)) std::fprintf(stderr, "       实得 %.12f\n", vol);
      CHECK(near(area, 6.0, 1e-9), "凸包表面积 = 6.0");
      CHECK(nf >= 6, "面数 >= 6");
    }
  }

  // ③ 正四面体（边长 = sqrt(2)），体积闭式解 = 1/3
  {
    coordT pts[12] = {
        0, 0, 0,
        1, 1, 0,
        1, 0, 1,
        0, 1, 1,
    };
    int nv = 0, nf = 0; double vol = 0, area = 0;
    int rc = hull(3, 4, pts, &nv, &nf, &vol, &area);
    CHECK(rc == 0, "qh_new_qhull 计算四面体凸包返回 0");
    if (rc == 0) {
      CHECK(nv == 4, "四面体顶点数为 4");
      CHECK(nf == 4, "四面体面数为 4");
      CHECK(near(vol, 1.0 / 3.0, 1e-9), "四面体体积 = 1/3");
      if (!near(vol, 1.0 / 3.0, 1e-9))
        std::fprintf(stderr, "       实得 %.12f 期望 %.12f\n", vol, 1.0 / 3.0);
    }
  }

  if (failures) {
    std::fprintf(stderr, "\nqhull: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nqhull 2020.2.1 (上游 8.0.2): 全部断言通过\n");
  return 0;
}
