cmake_minimum_required(VERSION 3.16)
project(harmonyos_libaribcaption_test LANGUAGES C CXX)

# HarmonyOS 专项测试（可复现构建入口）
# 用法: cmake -S . -B build -DCMAKE_PREFIX_PATH=<conan 包 prefix> \
#         -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> && cmake --build build && ctest --test-dir build
find_package(libaribcaption REQUIRED)

add_executable(harmonyos_libaribcaption_test harmonyos_libaribcaption_test.c)
target_link_libraries(harmonyos_libaribcaption_test PRIVATE libaribcaption::libaribcaption)

enable_testing()
add_test(NAME harmonyos_libaribcaption_test COMMAND harmonyos_libaribcaption_test)
