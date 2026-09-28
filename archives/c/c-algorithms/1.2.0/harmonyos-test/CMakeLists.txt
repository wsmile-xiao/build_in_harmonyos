cmake_minimum_required(VERSION 3.16)
project(harmonyos_calg_test LANGUAGES C)

# HarmonyOS 专项测试（可复现构建入口）
# 用法: cmake -S . -B build -DCMAKE_PREFIX_PATH=<conan 包 prefix> \
#       -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> && cmake --build build
# 或直接: clang -I<prefix>/include/libcalg-1.0 harmonyos_calg_test.c <prefix>/lib/libcalg.a -o harmonyos_calg_test
find_package(c-algorithms REQUIRED)

add_executable(harmonyos_calg_test harmonyos_calg_test.c)
target_link_libraries(harmonyos_calg_test PRIVATE c-algorithms::c-algorithms)

enable_testing()
add_test(NAME harmonyos_calg_test COMMAND harmonyos_calg_test)