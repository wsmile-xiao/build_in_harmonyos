cmake_minimum_required(VERSION 3.15)
project(test_rapidobj CXX)

# Find the package via Conan-generated CMakeDeps
find_package(RapidObj REQUIRED)

add_executable(test_rapidobj test.cpp)
target_compile_features(test_rapidobj PRIVATE cxx_std_17)
target_link_libraries(test_rapidobj rapidobj::rapidobj)

# HarmonyOS 专项测试: quad 三角化几何等价验证 (R02 根因覆盖)
add_executable(test_ohos_quad test_ohos_quad.cpp)
target_compile_features(test_ohos_quad PRIVATE cxx_std_17)
target_link_libraries(test_ohos_quad rapidobj::rapidobj)

enable_testing()
add_test(NAME test_rapidobj COMMAND test_rapidobj)
add_test(NAME test_ohos_quad COMMAND test_ohos_quad)
