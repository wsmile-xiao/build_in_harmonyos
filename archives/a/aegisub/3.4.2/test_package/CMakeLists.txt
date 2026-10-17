cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

# 真实链接 libaegisub 核心库并调用其 API（R34 非空壳）
find_package(aegisub REQUIRED)

add_executable(test_aegisub test_aegisub.cpp)
target_link_libraries(test_aegisub PRIVATE aegisub::aegisub)

# 产物验证：校验 libaegisub.a 为合法 ar 归档（R34 补充）
add_executable(elf_check elf_check.c)
