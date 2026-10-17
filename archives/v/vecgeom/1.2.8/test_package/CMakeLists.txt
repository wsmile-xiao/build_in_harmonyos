cmake_minimum_required(VERSION 3.15)
project(test_vecgeom CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 通过 Conan 生成的 CMakeDeps 找到被测包（VecGeom::vecgeom）
find_package(VecGeom REQUIRED)

# L1 消费者测试：真实调用 VecGeom API（非空壳，PF3 前置门禁）
add_executable(test_vecgeom test_vecgeom.cpp)
target_link_libraries(test_vecgeom PRIVATE VecGeom::vecgeom)

enable_testing()
add_test(NAME test_vecgeom COMMAND test_vecgeom)

# 鸿蒙特有测试用例：仅 OHOS 目标构建/运行，验证编译期平台识别 + 运行时几何导航
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
  add_executable(test_ohos test_ohos.cpp)
  target_link_libraries(test_ohos PRIVATE VecGeom::vecgeom)
  add_test(NAME test_ohos COMMAND test_ohos)
endif()
