cmake_minimum_required(VERSION 3.15)
project(test_gcem CXX)

# 通过 Conan 生成的 CMakeDeps 查找 gcem 包
find_package(gcem REQUIRED)

add_executable(test_gcem test_gcem.cpp)
target_link_libraries(test_gcem gcem::gcem)

# 鸿蒙特有测试：独立可执行目标，验证 __OHOS__/__aarch64__ 平台宏 + gcem API 实测
add_executable(harmonyos_specific_test harmonyos_specific_test.cpp)
target_link_libraries(harmonyos_specific_test gcem::gcem)

enable_testing()
add_test(NAME test_gcem COMMAND test_gcem)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)