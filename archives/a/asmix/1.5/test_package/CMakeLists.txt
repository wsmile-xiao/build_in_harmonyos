cmake_minimum_required(VERSION 3.15)
project(test_asmix C)

# asmix 为 package_type=application（无 CMakeDeps target），直接编译测试程序
add_executable(test_asmix test.c)
# 编译期注入 asmix 二进制路径（test_package 通过 conan runenv 提供）
if(NOT DEFINED ASMIX_BIN_PATH)
  set(ASMIX_BIN_PATH "$ENV{ASMIX_BIN_PATH}")
endif()
target_compile_definitions(test_asmix PRIVATE ASMIX_BIN_PATH="${ASMIX_BIN_PATH}")

enable_testing()
add_test(NAME test_asmix COMMAND test_asmix)
