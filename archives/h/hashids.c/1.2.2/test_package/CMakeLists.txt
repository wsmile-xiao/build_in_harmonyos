cmake_minimum_required(VERSION 3.15)
project(test_hashids.c C)

# 通过 Conan 生成的 CMakeDeps 查找 hashids.c 包
find_package(hashids.c REQUIRED)

add_executable(test_hashids.c test.c)
target_link_libraries(test_hashids.c hashids.c::hashids.c)

# 鸿蒙特有测试：独立可执行目标，验证 __OHOS__/__aarch64__ 平台宏 + hashids API 设备实测
add_executable(harmonyos_specific_test harmonyos_specific_test.c)
target_link_libraries(harmonyos_specific_test hashids.c::hashids.c)

enable_testing()
add_test(NAME test_hashids.c COMMAND test_hashids.c)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)