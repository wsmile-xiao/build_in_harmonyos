// 鸿蒙特有测试用例（仅 OPENHARMONY/OHOS 目标构建并运行）：
//   1. 编译期：断言 __OHOS__ 已定义（确认确实面向鸿蒙目标编译）
//   2. 运行时：在鸿蒙上真实构建世界几何并做一次点定位，验证被测包的运行时可用性
//      （动态库加载、libc++ 下的模板实例化、new/delete 路径）
#include <cassert>
#include <cstdio>
#include <sys/utsname.h>

#include <VecGeom/base/Vector3D.h>
#include <VecGeom/management/GeoManager.h>
#include <VecGeom/volumes/Box.h>
#include <VecGeom/volumes/LogicalVolume.h>
#include <VecGeom/volumes/PlacedVolume.h>

int main()
{
#if !defined(__OHOS__)
  std::printf("test_ohos: __OHOS__ not defined -> not a HarmonyOS target\n");
  return 1;
#else
  struct utsname u;
  assert(uname(&u) == 0);
  std::printf("test_ohos: uname sysname=%s machine=%s\n", u.sysname, u.machine);

  using namespace vecgeom;

  LogicalVolume *lbox  = new LogicalVolume("lbox", new UnplacedBox(20., 30., 40.));
  VPlacedVolume *pbox  = lbox->Place();
  GeoManager::Instance().SetWorldAndClose(pbox);

  Vector3D<Precision> inside(0, 0, 0), outside(100, 0, 0);
  assert(pbox->GetLogicalVolume() == lbox);
  assert(pbox->Inside(inside) == EInside::kInside);
  assert(pbox->Inside(outside) == EInside::kOutside);

  std::printf("test_ohos: OHOS navigation OK (sysname=%s)\n", u.sysname);
  return 0;
#endif
}
