cmake_minimum_required(VERSION 3.15)
project(test_boost_system CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(boost_system_pkg REQUIRED CONFIG COMPONENTS system)

add_executable(test_boost_system test_boost_system.cpp)
target_link_libraries(test_boost_system PRIVATE boost_system_pkg::system)
# OHOS musl: 测试二进制静态链接 libc++（动态依赖 libc++_shared.so 在
# conan buildenv / CI 环境下因 LD_LIBRARY_PATH 解析问题加载失败 rc=127，
# 静态打入 C++ 运行时后仅需 libc.so，可在任意环境直接运行）。
# 注：OHOS 适配版 conan 将 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS。
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_boost_system PRIVATE -static-libstdc++)
endif()

enable_testing()
add_test(NAME boost_system_test COMMAND test_boost_system)
