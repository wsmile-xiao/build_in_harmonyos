cmake_minimum_required(VERSION 3.16)
project(compile_time_regular_test_package CXX)

find_package(compile-time-regular REQUIRED CONFIG)

add_executable(test_ctre test_ctre.cpp)
target_link_libraries(test_ctre PRIVATE compile-time-regular::compile-time-regular)

# CTRE 官方核心标准 C++17（fixed_string NTTP 路径，与 CI profile cppstd=17 一致）
set_target_properties(test_ctre PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF)

# OHOS：测试二进制静态链接 libc++ 运行时（-static-libstdc++），
# 运行时不依赖 LD_LIBRARY_PATH 指向 SDK 的 libc++_shared.so——
# conanrun 环境不含 profile buildenv 的 SDK 库路径，动态链接会导致
# "Error loading shared library libc++_shared.so" (rc=127)。
target_link_options(test_ctre PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME ctre_smoke COMMAND test_ctre)
