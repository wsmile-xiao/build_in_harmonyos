# C++23（SET(CMAKE_CXX_STANDARD 23)）需 CMake >= 3.20（P3 审查修复：3.15 -> 3.20）
cmake_minimum_required(VERSION 3.20)
project(harmonyos_libfex_test CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 通过 Conan 生成的目标引用 libfex（含 liburing 运行时）
find_package(libfex REQUIRED)

add_executable(harmonyos_libfex_test harmonyos_libfex_test.cpp)
target_link_libraries(harmonyos_libfex_test PRIVATE libfex::libfex)
# W4 审计修复（R02）：断言（assert）在 Release/-DNDEBUG 下为 no-op，R02 回归
# 断言（混合状态赋值、or_else 值/错误态）必须真实执行，故强制启用 assert。
target_compile_options(harmonyos_libfex_test PRIVATE -UNDEBUG)

enable_testing()
add_test(NAME harmonyos_libfex_test COMMAND harmonyos_libfex_test)