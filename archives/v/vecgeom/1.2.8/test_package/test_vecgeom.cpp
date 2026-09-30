// test_package 消费者测试：真实调用 VecGeom 公开 API（非空壳）。
// 校验 Box 的几何量（Capacity/SurfaceArea/Inside/Extent）与上游 TestBox 一致。
#include <cassert>
#include <cstdio>

#include <VecGeom/base/Vector3D.h>
#include <VecGeom/volumes/Box.h>

int main()
{
  using Precision = vecgeom::Precision;
  using Vec3      = vecgeom::Vector3D<Precision>;

  vecgeom::SimpleBox box("consumer_box", 20., 30., 40.);

  // 与上游 test/unit_tests/TestBox.cpp 相同的期望值
  assert(box.Capacity() == 192000);
  assert(box.SurfaceArea() == 20800);

  assert(box.Inside(Vec3(0, 0, 0)) == vecgeom::EInside::kInside);
  assert(box.Inside(Vec3(0, 0, 40)) == vecgeom::EInside::kSurface);
  assert(box.Inside(Vec3(100, 0, 0)) == vecgeom::EInside::kOutside);

  Vec3 minExtent, maxExtent;
  box.Extent(minExtent, maxExtent);
  assert(minExtent == Vec3(-20, -30, -40));
  assert(maxExtent == Vec3(20, 30, 40));

  std::printf("vecgeom consumer test OK: capacity=%.0f surface=%.0f\n",
              static_cast<double>(box.Capacity()),
              static_cast<double>(box.SurfaceArea()));
  return 0;
}
