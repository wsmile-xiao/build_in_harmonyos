cmake_minimum_required(VERSION 3.15)
project(test_offbrand-lib C)

# Find the package via Conan-generated CMakeDeps
find_package(offbrand-lib REQUIRED)

add_executable(test_offbrand-lib test.c)
target_link_libraries(test_offbrand-lib offbrand-lib::offbrand-lib)

# HarmonyOS 专项测试：引用计数 / obmap / obstring 正则（OHOS musl 运行时）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos offbrand-lib::offbrand-lib)

enable_testing()
add_test(NAME test_offbrand-lib COMMAND test_offbrand-lib)
add_test(NAME test_ohos COMMAND test_ohos)
