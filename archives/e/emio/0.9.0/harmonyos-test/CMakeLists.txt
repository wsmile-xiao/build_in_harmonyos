cmake_minimum_required(VERSION 3.16)
project(emio_harmonyos_test LANGUAGES CXX)

# HarmonyOS 专项测试（可复现构建入口）
# 用法: cmake -S . -B build -DCMAKE_PREFIX_PATH=<emio 包 prefix> && cmake --build build
# 或直接: clang++ -std=gnu++20 -I<emio include> harmonyos_emio_test.cpp -o harmonyos_emio_test
find_package(emio REQUIRED)

add_executable(harmonyos_emio_test harmonyos_emio_test.cpp)
target_link_libraries(harmonyos_emio_test PRIVATE emio::emio)
target_compile_features(harmonyos_emio_test PRIVATE cxx_std_20)

enable_testing()
add_test(NAME harmonyos_emio_test COMMAND harmonyos_emio_test)