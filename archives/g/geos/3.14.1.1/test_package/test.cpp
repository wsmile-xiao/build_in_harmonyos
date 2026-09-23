#include <stdint.h>
#include <stddef.h>
#include <geos_c.h>

#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>

// GEOS 3.14.1 —— 真实几何计算验证（非 dlopen 空壳）。
// 全部用闭式解对账：
//   ① 版本号读得出且为 3.14.x
//   ② 10×10 正方形面积 = 100、周长 = 40
//   ③ 两个重叠正方形求交 → 面积恰为重叠部分
//   ④ 点在多边形内/外判定
//   ⑤ 两点距离 = 5（3-4-5 直角三角形）
//   ⑥ WKT 往返：写出再读回，面积不变
//   ⑦ 缓冲区：半径 1 的点缓冲面积 ≈ π（分段数足够时）
//   ⑧ 错误路径：畸形 WKT 必须解析失败且 notice/error handler 被调用

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

static bool near(double a, double b, double eps = 1e-9) {
  return std::fabs(a - b) < eps;
}

static int error_calls = 0;

static void notice_fn(const char *fmt, ...) {
  (void)fmt;
}
static void error_fn(const char *fmt, ...) {
  ++error_calls;
  (void)fmt;
}

int main() {
  initGEOS(notice_fn, error_fn);

  // ①
  const char *ver = GEOSversion();
  std::printf("     GEOS 版本: %s\n", ver ? ver : "(null)");
  CHECK(ver != nullptr && std::strncmp(ver, "3.14", 4) == 0, "GEOSversion() 为 3.14.x");

  GEOSWKTReader *rd = GEOSWKTReader_create();
  GEOSWKTWriter *wr = GEOSWKTWriter_create();
  CHECK(rd != nullptr && wr != nullptr, "WKT reader/writer 创建成功");

  // ② 10×10 正方形
  GEOSGeometry *sq = GEOSWKTReader_read(
      rd, "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))");
  CHECK(sq != nullptr, "解析 10×10 正方形 WKT");
  double area = 0, len = 0;
  if (sq) {
    CHECK(GEOSArea(sq, &area) == 1 && near(area, 100.0, 1e-9), "面积 = 100");
    if (!near(area, 100.0, 1e-9)) std::fprintf(stderr, "       实得 %.9f\n", area);
    CHECK(GEOSLength(sq, &len) == 1 && near(len, 40.0, 1e-9), "周长 = 40");
  }

  // ③ 求交：与 (5 5)-(15 15) 正方形相交 → 5×5 = 25
  if (sq) {
    GEOSGeometry *sq2 = GEOSWKTReader_read(
        rd, "POLYGON((5 5, 15 5, 15 15, 5 15, 5 5))");
    GEOSGeometry *inter = sq2 ? GEOSIntersection(sq, sq2) : nullptr;
    double ia = 0;
    CHECK(inter != nullptr && GEOSArea(inter, &ia) == 1 && near(ia, 25.0, 1e-9),
          "两正方形交集面积 = 25");
    if (inter && !near(ia, 25.0, 1e-9)) std::fprintf(stderr, "       实得 %.9f\n", ia);
    if (inter) GEOSGeom_destroy(inter);
    if (sq2) GEOSGeom_destroy(sq2);
  }

  // ④ 点在多边形内/外
  if (sq) {
    GEOSGeometry *pin = GEOSWKTReader_read(rd, "POINT(5 5)");
    GEOSGeometry *pout = GEOSWKTReader_read(rd, "POINT(50 50)");
    CHECK(pin && GEOSContains(sq, pin) == 1, "POINT(5 5) 在正方形内");
    CHECK(pout && GEOSContains(sq, pout) == 0, "POINT(50 50) 在正方形外");
    if (pin) GEOSGeom_destroy(pin);
    if (pout) GEOSGeom_destroy(pout);
  }

  // ⑤ 3-4-5
  {
    GEOSGeometry *a = GEOSWKTReader_read(rd, "POINT(0 0)");
    GEOSGeometry *b = GEOSWKTReader_read(rd, "POINT(3 4)");
    double d = 0;
    CHECK(a && b && GEOSDistance(a, b, &d) == 1 && near(d, 5.0, 1e-9),
          "GEOSDistance((0,0),(3,4)) = 5");
    if (a) GEOSGeom_destroy(a);
    if (b) GEOSGeom_destroy(b);
  }

  // ⑥ WKT 往返
  if (sq && wr) {
    GEOSWKTWriter_setTrim(wr, 1);
    char *out = GEOSWKTWriter_write(wr, sq);
    CHECK(out != nullptr && std::strstr(out, "POLYGON") != nullptr,
          "写出的 WKT 含 POLYGON");
    if (out) {
      GEOSGeometry *back = GEOSWKTReader_read(rd, out);
      double ba = 0;
      CHECK(back && GEOSArea(back, &ba) == 1 && near(ba, 100.0, 1e-9),
            "WKT 往返后面积仍为 100");
      if (back) GEOSGeom_destroy(back);
      GEOSFree(out);
    }
  }

  // ⑦ 缓冲区：点缓冲半径 1，分段数 64 → 面积逼近 π
  {
    GEOSGeometry *p = GEOSWKTReader_read(rd, "POINT(0 0)");
    GEOSGeometry *buf = p ? GEOSBuffer(p, 1.0, 64) : nullptr;
    double ba = 0;
    CHECK(buf != nullptr && GEOSArea(buf, &ba) == 1, "点缓冲生成成功");
    if (buf) {
      const double PI = 3.14159265358979323846;
      CHECK(std::fabs(ba - PI) < 1e-3, "半径 1 的缓冲面积 ≈ π（误差 < 1e-3）");
      if (std::fabs(ba - PI) >= 1e-3)
        std::fprintf(stderr, "       实得 %.9f 期望 %.9f\n", ba, PI);
      GEOSGeom_destroy(buf);
    }
    if (p) GEOSGeom_destroy(p);
  }

  // ⑧ 错误路径
  {
    const int before = error_calls;
    GEOSGeometry *bad = GEOSWKTReader_read(rd, "POLYGON((这不是 WKT");
    CHECK(bad == nullptr, "畸形 WKT 解析返回 NULL");
    CHECK(error_calls > before, "error handler 被调用（证明回调真的接上了）");
    if (bad) GEOSGeom_destroy(bad);
  }

  if (sq) GEOSGeom_destroy(sq);
  if (wr) GEOSWKTWriter_destroy(wr);
  if (rd) GEOSWKTReader_destroy(rd);
  finishGEOS();

  if (failures) {
    std::fprintf(stderr, "\ngeos: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\ngeos 3.14.1: 全部断言通过\n");
  return 0;
}
